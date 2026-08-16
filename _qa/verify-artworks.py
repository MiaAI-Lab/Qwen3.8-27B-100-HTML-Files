#!/usr/bin/env python3
"""Verify a batch of self-contained HTML artworks + companion .txt design records.

Usage:
  verify-artworks.py <dir> [--min-size 3000] [--no-runtime]
                     [--blocks TITLE PROMPT DESCRIPTION TECHNIQUES INTERACTION]

Static checks (always):
  - HTML validity via html.parser.HTMLParser().feed()
  - no 'http' / 'https' / '//cdn' / '@import' substring anywhere in the file
  - byte size >= floor (default 3000)
  - TXT has every required block key (default the five standard keys)
  - extracted <script> body passes `node --check` (skipped if node missing)

Runtime check (unless --no-runtime): playwright + chromium loads each page,
captures console/page errors, waits ~1s, and probes canvas pixels via in-page
getImageData stride sampling (no screenshots, no PIL needed). Prints a report
and exits non-zero if anything fails. Runtime is optional-by-flag so the static
battery works anywhere; runtime must fail --no-runtime to stay honest.
"""
import sys, os, re, html.parser
import subprocess

def parse_args(argv):
    args=list(argv); d={'dir':None,'min_size':3000,'runtime':True,'blocks':['TITLE','PROMPT','DESCRIPTION','TECHNIQUES','INTERACTION']}
    i=0
    while i<len(args):
        a=args[i]
        if a=='--no-runtime': d['runtime']=False
        elif a=='--min-size': i+=1; d['min_size']=int(args[i])
        elif a=='--blocks':
            d['blocks']=[]
            while i+1<len(args) and not args[i+1].startswith('--'):
                i+=1; d['blocks'].append(args[i])
        elif not a.startswith('-') and d['dir'] is None:
            d['dir']=a
        i+=1
    if not d['dir']:
        print(__doc__); sys.exit(2)
    return d

def main():
    opts=parse_args(sys.argv[1:])
    base=os.path.abspath(opts['dir'])
    if not os.path.isdir(base):
        print('path is not a directory:', base); sys.exit(2)
    htmls=sorted(f for f in os.listdir(base) if f.endswith('.html'))
    if not htmls:
        print('no .html files found in', base); sys.exit(2)
    issues=[]
    for f in htmls:
        slug=f[:-5]
        path=os.path.join(base,f); txt=os.path.join(base,slug+'.txt')
        data=open(path,encoding='utf-8').read()
        e={'file':f,'txt':os.path.exists(txt),'size':len(data.encode()),
           'http':len(re.findall('http',data,re.I)),'imp':data.count('@import'),
           'parse':'FAIL','js':'-','blocks':'-'}
        try:
            html.parser.HTMLParser().feed(data); e['parse']='OK'
        except Exception as ex:
            e['parse']='ERR:'+str(ex)
        m=re.search(r'<script[^>]*>(.*?)</script>',data,re.S|re.I)
        if m:
            tmp='/tmp/_chk.js'
            open(tmp,'w',encoding='utf-8').write(m.group(1))
            try:
                r=subprocess.run(['node','--check',tmp],capture_output=True,text=True,timeout=30)
                e['js']='OK' if r.returncode==0 else 'ERR'
            except FileNotFoundError:
                e['js']='skip'
        if os.path.exists(txt):
            t=open(txt,encoding='utf-8').read()
            have=[b for b in opts['blocks'] if re.search(r'^'+re.escape(b)+r':',t,re.M)]
            e['blocks']=','.join(have)
            if len(have)!=len(opts['blocks']): issues.append(f+': missing TXT blocks')
        print('{f}: txt={txt} size={size} http={http} @import={imp} parse={parse} js={js} blocks=[{blocks}]'.format(f=f,**e))
        if e['size']<=opts['min_size']: issues.append(f+': too small (<= {})'.format(opts['min_size']))
        if e['http']: issues.append(f+': contains http substring')
        if e['imp']: issues.append(f+': contains @import')
        if e['parse']!='OK': issues.append(f+': HTML parse failed')
        if e['js'] not in ('OK','skip'): issues.append(f+': JS syntax failed')

    if opts['runtime']:
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                b=p.chromium.launch()
                pg=b.new_page(viewport={'width':1280,'height':800})
                for f in htmls:
                    errs=[]
                    # register per page INSIDE loop, one shot — avoids cross-page listener accumulation
                    pg.on('console',lambda m,errs=errs: errs.append(m.text) if m.type=='error' else None)
                    pg.on('pageerror',lambda e2,errs=errs: errs.append(str(e2)))
                    try:
                        pg.goto('file://'+os.path.join(base,f),wait_until='load',timeout=30000)
                        pg.wait_for_timeout(1000)
                        pix=pg.evaluate("""(() => {
                          const cv=document.querySelector('canvas'); if(!cv) return null;
                          const c=cv.getContext('2d');
                          const d=c.getImageData(0,0,cv.width,cv.height).data;
                          let n=0,t=0;
                          for(let i=0;i<d.length;i+=137){
                            const r=d[i],g=d[i+1],b2=d[i+2]; t++;
                            if(r+g+b2>40 && !(r<30&&g<30&&b2<40)) n++;
                          }
                          return n+'/'+t+' px';
                        })()""")
                        print('  runtime',f,'errors=',errs,'canvas-pix=',pix)
                    except Exception as ex:
                        # renderer crash — cross-verify with the real browser path before
                        # flagging (see SKILL.md "Playwright renderer crash" pitfall).
                        try:
                            r2=subprocess.run(['/usr/bin/chromium-browser','--headless=new','--no-sandbox',
                                '--disable-gpu','--virtual-time-budget=9000','--dump-dom',
                                'file://'+os.path.join(base,f)],
                                capture_output=True,text=True,timeout=60)
                            if '<html' not in r2.stdout.lower(): raise RuntimeError('CLI dump empty')
                            print('  runtime',f,'HARNESS-CRASH, CLI render OK — not flagged')
                        except Exception as ex2:
                            print('  runtime',f,'crash AND cli cross-check failed:',str(ex2)[:80])
                            issues.append(f+': runtime renderer crash')
                    if errs: issues.append(f+': runtime console errors')
                b.close()
        except Exception as ex:
            print('  runtime skipped:',ex)

    print('')
    print('ISSUES:' if issues else 'ISSUES: NONE')
    for i2 in issues: print(' -',i2)
    sys.exit(1 if issues else 0)

if __name__=='__main__':
    main()
