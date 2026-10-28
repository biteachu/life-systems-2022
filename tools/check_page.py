"""Reproducible offline browser checks. Install playwright separately to run."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "review"
OUT.mkdir(exist_ok=True)
results = []

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    for width in (1440, 768, 390):
        context = browser.new_context(viewport={"width": width, "height": 960})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "index.html").as_uri())
        assert page.locator("h1").count() == 1
        assert page.locator(".question").count() == 3
        assert page.locator(".standard").count() == 7
        assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), width
        for index, correct in enumerate(("2", "3", "1")):
            question = page.locator(".question").nth(index)
            assert not question.locator("details").evaluate("el => el.open")
            question.locator(f'input[value="{correct}"]').check()
            assert question.locator("input:checked").count() == 1
            question.locator('input[value="4"]').check()
            assert question.locator("input:checked").count() == 1
            question.locator(f'input[value="{correct}"]').check()
            question.locator("summary").click()
            assert question.locator("details").evaluate("el => el.open")
            assert question.locator(".answer-body").is_visible()
            question.locator("summary").click()
            assert not question.locator("details").evaluate("el => el.open")
        # The HTML disclosure must work from the keyboard, without JavaScript.
        first = page.locator(".answer summary").first
        first.focus()
        page.keyboard.press("Enter")
        assert page.locator(".answer").first.evaluate("el => el.open")
        assert first.evaluate("el => getComputedStyle(el).outlineStyle") != "none"
        page.keyboard.press("Enter")
        for target in ("concepts", "quiz"):
            page.locator(f'.nav-links a[href="#{target}"]').click()
            assert page.url.endswith("#" + target)
        page.locator(".source-details summary").click()
        assert page.locator(".standard").first.is_visible()
        page.locator(".source-details summary").click()
        page.evaluate("window.scrollTo(0,0)")
        page.screenshot(path=str(OUT / f"page-{width}.png"), full_page=True)
        if width == 1440:
            button = page.locator(".btn-primary")
            before = button.evaluate("el => getComputedStyle(el).backgroundColor")
            button.hover()
            page.wait_for_timeout(250)
            after = button.evaluate("el => getComputedStyle(el).backgroundColor")
            assert before != after
            page.screenshot(path=str(OUT / "button-hover.png"))
            page.emulate_media(reduced_motion="reduce")
            assert button.evaluate("el => getComputedStyle(el).transform") == "none"
        assert not errors, errors
        results.append({"width": width, "overflow": False, "radio_and_answers": "passed", "keyboard": "passed", "anchors": "passed", "page_errors": errors})
        context.close()
    browser.close()

(OUT / "checks.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
