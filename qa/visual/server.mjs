import { createServer } from 'node:http';
import { readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve, join, extname, sep } from 'node:path';
import { execFileSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
export const approvedSHA = 'a5e524392abcf89ffd5ace2a18218a6b59ed3b61';
export function startPreview({renderCurrent=true}={}) {
  const root = process.cwd();
  const temp = mkdtempSync(join(tmpdir(), 'rollsbar-approved-'));
  try {
    execFileSync('git', ['archive', '--format=tar', `--output=${join(temp,'approved.tar')}`, approvedSHA]);
    execFileSync('tar', ['-xf', join(temp,'approved.tar'), '-C', temp]);
    const php = process.env.ROLLSBAR_PHP || join(root,'qa/.runtime/php/php.exe');
    const current = renderCurrent ? execFileSync(php, ['qa/visual/preview.php', root], { encoding:'utf8', maxBuffer:8e6 }) : null;
    if (renderCurrent && (!current.startsWith('<!doctype html>') || /Fatal error|Warning:/.test(current))) throw Error('PHP fixture did not render cleanly');
    const types = {'.html':'text/html; charset=utf-8','.js':'application/javascript','.css':'text/css','.png':'image/png','.webp':'image/webp'};
    const carts=new Map();
    const server = createServer(async(req,res) => {
      try {
        const url = new URL(req.url,'http://localhost');
        if(url.pathname==='/fixture-cart'&&renderCurrent){
          const session=req.headers.cookie?.match(/rollsbar_fixture=([^;]+)/)?.[1]||randomUUID();
          const chunks=[];for await(const chunk of req)chunks.push(chunk);
          const form=new URLSearchParams(Buffer.concat(chunks).toString());
          if(form.get('nonce')!=='local-fixture'){res.writeHead(403);res.end();return;}
          const result=JSON.parse(execFileSync(php,['qa/visual/cart-fixture.php',root],{input:JSON.stringify({request:JSON.parse(form.get('request')),...(carts.get(session)||{})}),encoding:'utf8'}));
          carts.set(session,{items:result.items,session:result.session});delete result.items;delete result.session;
          res.setHeader('Set-Cookie',`rollsbar_fixture=${session}; Path=/; SameSite=Strict`);
          res.setHeader('Content-Type','application/json');res.end(JSON.stringify(result));return;
        }
        if (url.pathname==='/health') { res.end('ready'); return; }
        const approved = url.pathname.startsWith('/approved/');
        const base = approved ? temp : root;
        const pathname = url.pathname.replace(/^\/(approved|current)/,'');
        if (!approved && (pathname==='/' || pathname==='/index.html')) {
          if(current===null) {res.writeHead(403);res.end('Current rendering is disabled during baseline generation');return;}
          res.setHeader('content-type',types['.html']);res.end(current);return;
        }
        const file = resolve(base, '.'+decodeURIComponent(pathname.endsWith('/')?pathname+'index.html':pathname));
        if (!file.startsWith(base+sep)) {res.writeHead(403);res.end();return;}
        res.setHeader('content-type',types[extname(file)] || 'application/octet-stream');
        res.end(readFileSync(file));
      } catch {res.writeHead(404);res.end();}
    });
    // Current theme URLs are root-relative; approved resources remain under /approved/.
    return new Promise((resolveReady,reject) => {
      server.once('error',error=>{rmSync(temp,{recursive:true,force:true});reject(error);});
      server.listen(4178,'127.0.0.1',()=>resolveReady({
        close:()=>new Promise(done=>server.close(()=>{rmSync(temp,{recursive:true,force:true});done();})),
        temp
      }));
    });
  } catch(error) { rmSync(temp,{recursive:true,force:true}); throw error; }
}
