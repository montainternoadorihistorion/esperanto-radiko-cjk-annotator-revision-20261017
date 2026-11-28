"""Verify the deployed release through each app's public URL and real downloads."""
import argparse
import asyncio
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlsplit

from playwright.async_api import Error as BrowserError, TimeoutError as BrowserTimeout, async_playwright

FIXTURE = json.loads(Path(__file__).with_name("expectations.json").read_bytes())
HOSTS = {
    **{f"forward-{lang}": f"https://esperanto-cjk-revision-{lang.lower()}-20261017.streamlit.app/"
       for lang in ("JA", "ZH", "KO")},
    **{f"inverse-{lang}": f"https://esperanto-reverter-revision-{lang.lower()}-20261018.streamlit.app/"
       for lang in ("JA", "ZH")},
}
MARKERS = {"JA": ("新版", "旧版"), "ZH": ("新版", "旧版"), "KO": ("신판", "구판")}
CONFIRM = {"JA": "保存内容を確認", "ZH": "确认保存内容", "KO": "저장 내용 확인"}
MODE_INDEX = {"ruby": 0, "kanji": 1, "pure": 2}
STARTUP_CAPTION = {
    "JA":"下の入力欄に文章を入れ、「🔁 変換する」を押してください。",
    "ZH":"请在下方输入文本，然后点击「🔁 开始转换」。",
    "KO":"아래 입력란에 문장을 넣은 뒤 「🔁 변환하기」를 누르세요.",
}
WAKE = re.compile(r"^Yes,\s*get this app back up!?$", re.I)


class CheckFailure(Exception):
    pass


def digest(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def case_key(case):
    return case["edition"] + "_" + case["mode"]


def require(condition, message):
    if not condition:
        raise CheckFailure(message)


def describe(exc):
    if isinstance(exc, CheckFailure):
        return str(exc)
    if isinstance(exc, (TimeoutError, BrowserTimeout)):
        return "Timed out waiting for this browser operation"
    # Playwright call logs can include signed iframe URLs. Keep only the type.
    return "Browser operation failed (" + type(exc).__name__ + ")"


async def enter_app(page, url, visit):
    reply = await page.goto(url, wait_until="commit", timeout=35000)
    require(reply is not None, "No HTTP response from the public URL")
    visit["outer_http"] = reply.status
    require(reply.status < 400, f"Public URL returned HTTP {reply.status}")
    deadline = time.monotonic() + 95
    while time.monotonic() < deadline:
        for frame in page.frames:
            try:
                exceptions = frame.locator('[data-testid="stException"]:visible')
                require(not await exceptions.count(), "Streamlit displayed an app exception")
                if await frame.locator('textarea:visible').count() and await frame.get_by_role("combobox").count():
                    require(page.url == url, "Top-level address differs from the registered public URL")
                    return frame
                if not visit["wake_clicked"]:
                    button = frame.get_by_role("button", name=WAKE)
                    if await button.count() and await button.first.is_visible():
                        await button.first.click(timeout=3000)
                        visit["wake_clicked"] = True
            except BrowserError:
                if not frame.is_detached():
                    raise
        await asyncio.sleep(0.8)
    visit["frame_hosts"] = sorted({urlsplit(f.url).hostname for f in page.frames if urlsplit(f.url).hostname})
    raise CheckFailure("Public URL did not present the application's input and edition selector")


async def choose(frame, lang, case):
    marker = MARKERS[lang][case["edition"] == "legacy"]
    select = frame.locator("[data-testid=stSelectbox]").first
    group = frame.locator('[role=radiogroup]').first
    for _ in range(3):
        if marker not in (await select.inner_text()).strip().splitlines()[-1]:
            await select.get_by_role("combobox").click()
            await frame.get_by_role("option").filter(has_text=marker).click()
            await asyncio.sleep(1.2)
        if case["mode"] != "reverse":
            index = MODE_INDEX[case["mode"]]
            if not await group.locator("input").nth(index).is_checked():
                await group.locator("label").nth(index).click()
                await asyncio.sleep(1.2)
            if not await group.locator("input").nth(index).is_checked():
                continue
        selected = (await select.inner_text()).strip().splitlines()[-1]
        if marker in selected:
            return selected
    raise CheckFailure("App did not select the requested edition and mode")


async def verify_case(page, frame, url, lang, source, case, output, obs):
    if case["mode"] == "frontend":
        require(page.url == url, "Public address changed")
        obs.update(stage="complete", startup_caption=STARTUP_CAPTION[lang])
        return
    frame_dialog = frame.get_by_role("dialog")
    if await frame_dialog.count() and await frame_dialog.first.is_visible():
        await page.keyboard.press("Escape")
        await frame_dialog.first.wait_for(state="hidden")
    obs["stage"] = "select"
    obs["selected_edition"] = await choose(frame, lang, case)
    field = frame.locator("textarea").first
    if await field.input_value() != source:
        await field.fill(source)
        await field.press("Tab")
        await asyncio.sleep(0.8)
    obs["stage"] = "convert"
    await frame.locator("button[kind=primary]").first.click()
    result = frame.locator("textarea").nth(1)
    await result.wait_for(state="attached", timeout=65000)
    deadline = time.monotonic() + 16
    while True:
        actual = await result.input_value()
        obs["observed_output_sha256"] = digest(actual)
        if obs["observed_output_sha256"] == case["output_sha256"]:
            break
        if time.monotonic() >= deadline:
            raise CheckFailure("Displayed output differs from the checked release fixture")
        await asyncio.sleep(0.4)
    require(await field.input_value() == source, "Source text changed")
    require(page.url == url, "Public address changed during conversion")
    if "expected_text" in case:
        require(actual == case["expected_text"], "Plain output differs")
    if case["mode"] == "reverse":
        captions = await frame.locator("[data-testid=stCaptionContainer]").all_inner_texts()
        require(case["provenance"] in captions, "Displayed inverse edition or dictionary revision differs")
        obs["provenance"] = case["provenance"]
    if case["mode"] in ("kanji", "ruby"):
        obs["stage"] = "preview"
        preview = frame.locator("iframe[srcdoc]").first
        require(await preview.get_attribute("srcdoc") == actual, "HTML preview and displayed source differ")
        element = await preview.element_handle()
        nested = await element.content_frame()
        require(nested is not None and await nested.evaluate("document.documentElement.lang") == lang.lower(),
                "Preview language differs from the selected app")
    obs["stage"] = "download"
    await frame.get_by_role("button", name=CONFIRM[lang], exact=True).click()
    dialog = frame.get_by_role("dialog")
    await dialog.wait_for()
    if case["mode"] == "reverse":
        require(await dialog.locator("textarea").input_value() == actual, "Save preview differs from the restored text")
    button = dialog.locator("[data-testid=stDownloadButton]").locator("button,a").first
    async with page.expect_download(timeout=35000) as event:
        await button.click()
    download = await event.value
    require(await download.failure() is None, "Browser reported a failed download")
    obs["filename"] = download.suggested_filename
    require(obs["filename"] == case["filename"], "Filename differs from the selected edition")
    destination = output / case["filename"]
    await download.save_as(destination)
    content = destination.read_bytes()
    obs["bytes"] = len(content)
    obs["download_sha256"] = digest(content)
    if case["mode"] in ("kanji", "ruby"):
        stamp, separator, content = content.partition(b"\n")
        prefix = f"<!-- assignment-edition:{case['edition']} signature:{case['signature']} created-utc:"
        require(separator == b"\n" and stamp.startswith(prefix.encode()) and stamp.endswith(b"-->"),
                "HTML download lacks the expected edition and complete settings signature")
    obs["observed_core_sha256"] = digest(content)
    require(obs["observed_core_sha256"] == case["core_sha256"], "Downloaded content differs from the fixture")
    require(page.url == url, "Public address changed while saving")
    obs["stage"] = "complete"


async def visit_host(browser, url, lang, source, rows, output, report, save):
    visit = {"start":utc(), "wake_clicked":False, "http_errors":[], "network_failures":[]}
    report["visits"].append(visit)
    context = await browser.new_context(accept_downloads=True, viewport={"width":1440, "height":950})
    context.set_default_timeout(15000)
    page = await context.new_page()
    hostname = urlsplit(url).hostname

    def response_log(response):
        parts = urlsplit(response.url)
        if parts.hostname == hostname and response.status >= 400:
            sample = {"status":response.status, "path":parts.path[:180], "type":response.request.resource_type}
            if sample not in visit["http_errors"] and len(visit["http_errors"]) < 25:
                visit["http_errors"].append(sample)

    page.on("response", response_log)
    def request_failure(request):
        parts = urlsplit(request.url)
        if parts.hostname == hostname and len(visit["network_failures"]) < 15:
            code = re.search(r"net::ERR_[A-Z0-9_]+", request.failure or "")
            sample = {"path":parts.path[:180], "type":request.resource_type, "error":code[0] if code else "failed"}
            if sample not in visit["network_failures"]:
                visit["network_failures"].append(sample)

    page.on("requestfailed", request_failure)
    save()
    try:
        try:
            frame = await asyncio.wait_for(enter_app(page, url, visit), timeout=140)
        except (CheckFailure, BrowserError, TimeoutError) as exc:
            visit["startup_error"] = describe(exc)
            print("Startup:",visit["startup_error"],flush=True)
            for case in rows:
                report["records"][case_key(case)]["attempts"].append(
                    {"stage":"startup", "error":visit["startup_error"], "passed":False, "time":utc()})
            return
        visit["opened"] = True
        if rows[0]["mode"] != "reverse":
            marker = frame.locator("[data-testid=stCaptionContainer]").get_by_text(STARTUP_CAPTION[lang], exact=True)
            try:
                await marker.first.wait_for(state="visible", timeout=10000)
                visit["startup_caption"] = STARTUP_CAPTION[lang]
            except BrowserTimeout:
                visit["startup_caption"] = "Release caption not visible"
                for case in rows:
                    report["records"][case_key(case)]["attempts"].append(
                        {"stage":"frontend_release", "error":visit["startup_caption"], "passed":False, "time":utc()})
                return
        for case in rows:
            record = report["records"][case_key(case)]
            obs = {"passed":False, "time":utc(), "stage":"start"}
            record["attempts"].append(obs)
            save()
            try:
                await asyncio.wait_for(verify_case(page, frame, url, lang, source, case, output, obs), timeout=110)
                record["passed"] = obs["passed"] = True
            except (CheckFailure, BrowserError, TimeoutError) as exc:
                obs["error"] = describe(exc)
            save()
            print(case_key(case),obs["stage"],obs.get("error","PASS"),flush=True)
    finally:
        visit["end"] = utc()
        save()
        await context.close()


async def check(host, output, record_keys=()):
    kind, lang = host.split("-")
    url = HOSTS[host]
    rows = FIXTURE[kind][lang]
    if record_keys:
        available = {case_key(row):row for row in rows}
        if kind == "forward":
            available["public_frontend"] = {"edition":"public", "mode":"frontend"}
        rows = [available[name] for name in record_keys]
    source = FIXTURE[kind+"_source"]
    output.mkdir(parents=True, exist_ok=True)
    report = {"host":host, "public_url":url, "source":source, "start":utc(), "visits":[],
              "records":{case_key(c):{"passed":False, "attempts":[]} for c in rows}}
    path = output/"report.json"

    def save():
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n",encoding="utf-8")

    save()
    try:
        async with asyncio.timeout(18*60):
            async with async_playwright() as runtime:
                browser = await runtime.chromium.launch()
                try:
                    for attempt in range(2):
                        pending = [c for c in rows if not report["records"][case_key(c)]["passed"]]
                        if not pending:
                            break
                        if attempt:
                            await asyncio.sleep(12)
                        await visit_host(browser, url, lang, source, pending, output, report, save)
                finally:
                    await browser.close()
    except (TimeoutError, BrowserError, CheckFailure) as exc:
        report["host_error"] = describe(exc)
    finally:
        report["end"] = utc()
        report["passed"] = all(r["passed"] for r in report["records"].values()) and "host_error" not in report
        save()
        if os.getenv("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as stream:
                stream.write(f"### {host}\n\n| Edition and mode | Result |\n|---|---|\n")
                for name, rec in report["records"].items():
                    stream.write(f"| {name} | {'Passed' if rec['passed'] else 'Unverified'} |\n")
    return report["passed"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("host",choices=HOSTS)
    parser.add_argument("--results",type=Path,default=Path("cloud-qa-results"))
    parser.add_argument("--records", nargs="+", default=(), help="Previously unverified cases or public_frontend")
    options = parser.parse_args()
    raise SystemExit(0 if asyncio.run(check(options.host, options.results, options.records)) else 1)
