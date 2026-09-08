"""Optional UI smoke check; requires Playwright and installed Edge."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect


def main():
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto('http://localhost:5173')
        page.get_by_label('Backtest engine').select_option('cpp')
        with page.expect_response(lambda r:'/backtest/run' in r.url and r.request.method=='POST') as response:
            page.get_by_role('button',name='Run Backtest',exact=True).click()
        result=response.value.json()
        assert response.value.status==200,result
        assert result['evaluation']['engine']=='cpp'
        expect(page.get_by_role('status')).to_contain_text('Saved run')
        page.reload()
        saved=page.get_by_role('button',name=f"backtest · BTCUSDT · {result['run_id'][:8]}",exact=False)
        expect(saved).to_be_visible()
        saved.click()
        expect(page.get_by_role('status')).to_contain_text('Loaded saved backtest')
        Path('artifacts').mkdir(exist_ok=True)
        page.screenshot(path='artifacts/research-history.png',full_page=True)
        Path('artifacts/browser-saved-run.json').write_text(json.dumps({'run_id':result['run_id'],
            'dataset_id':result['dataset_id'],'engine_version':result['engine_version']},indent=2))
        assert not errors,errors
        browser.close()
    print('Passed: C++ backtest, saved result, history reload, and restored chart; no JavaScript errors.')


if __name__=='__main__':main()
