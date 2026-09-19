// Local fixture behavior only: no real auth, Runtime writes, or expiry guarantees.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const {JSDOM,VirtualConsole}=require(process.env.JSDOM_MODULE||'jsdom');
const html=fs.readFileSync(path.join(__dirname,'token-refresh.html'),'utf8');
let count=0;
function test(name,run){
 const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e));
 let network=0;
 const dom=new JSDOM(html,{runScripts:'dangerously',url:'http://localhost/token-refresh.html',virtualConsole:vc,beforeParse(w){for(const key of ['fetch','XMLHttpRequest','WebSocket','EventSource'])w[key]=()=>{network++;throw Error('No network permitted');};}});
 const w=dom.window,$=id=>w.document.getElementById(id),click=id=>$(id).click(),snapshot=()=>w.tokenDemo.snapshot;
 $('pause').checked=true;
 try{run({w,$,click,snapshot});assert.deepEqual(errors,[]);assert.equal(network,0);count++;console.log('PASS',name);}finally{w.close();}
}
test('fresh auth precedes one business write; receipt alone clears submitted draft',({$,click,snapshot})=>{
 const original=$('draft').value;click('send');click('send');assert.equal(snapshot().authCount,1);assert.equal(snapshot().writes,0);assert.equal($('draft').value,original);assert.equal($('return-receipt').disabled,true);
 click('return-auth');click('return-auth');assert.equal(snapshot().writes,1);assert.equal($('draft').value,original);click('return-receipt');assert.equal($('draft').value,'');assert.equal($('user-message').textContent,original);
});
test('failure retains input, old token and zero writes; explicit retry fetches again',({$,click,snapshot})=>{
 $('outcome').value='failure';const original=$('draft').value;click('send');click('return-auth');assert.equal(snapshot().phase,'failed');assert.equal(snapshot().writes,0);assert.equal($('draft').value,original);assert.equal($('token-value').value,'synthetic-old-token');
 click('fix-settings');click('save-settings');click('close-settings');click('send');assert.equal(snapshot().authCount,2);click('return-auth');assert.equal(snapshot().writes,1);
});
test('editing a newer draft survives delayed receipt',({$,click,snapshot})=>{click('send');$('draft').value='接下来检查西区';click('return-auth');click('return-receipt');assert.equal($('draft').value,'接下来检查西区');assert.equal(snapshot().writes,1);});
test('closing settings preserves send-owned auth',({click,snapshot})=>{click('send');click('settings');click('close-settings');assert.equal(snapshot().phase,'refreshing');click('return-auth');assert.equal(snapshot().writes,1);});
test('saving settings cancels preparation and stale result cannot submit',({$,click,snapshot})=>{const original=$('draft').value;click('send');click('settings');click('save-settings');click('return-auth');assert.equal(snapshot().writes,0);assert.equal(snapshot().phase,'ready');assert.equal($('draft').value,original);});
test('switching target cancels preparation without dropping draft',({$,click,snapshot})=>{const original=$('draft').value;click('send');click('other-chat');click('return-auth');assert.equal(snapshot().writes,0);assert.equal($('draft').value,original);});
test('IME and repeat Enter do not send; normal Enter submits once',({w,$,snapshot})=>{
 for(const detail of [{isComposing:true},{repeat:true},{shiftKey:true}])$('draft').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter',...detail}));assert.equal(snapshot().authCount,0);
 $('draft').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter'}));$('draft').dispatchEvent(new w.KeyboardEvent('keydown',{key:'Enter'}));assert.equal(snapshot().authCount,1);assert.equal(snapshot().writes,0);
});
test('initial refreshing and failure entries preserve their inspectable state',({w,$,snapshot})=>{w.tokenDemo.reset('token-refreshing');assert.equal(snapshot().phase,'refreshing');assert.equal(snapshot().writes,0);assert.equal($('pause').checked,true);w.tokenDemo.reset('token-failed');assert.equal(snapshot().phase,'failed');assert.equal(snapshot().writes,0);assert.ok($('draft').value);});
console.log(`${count} token fixture scenarios passed. No real auth or backend calls.`);
