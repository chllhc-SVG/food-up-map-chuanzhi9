'use strict';

const $ = id => document.getElementById(id);
const cities = {wuhan:{name:'武汉',lat:30.59,lon:114.30}, fuzhou:{name:'福州',lat:26.08,lon:119.30}};
const precision = {poi:'店铺点位',address:'地址参考',area:'片区参考',pending:'坐标待核'};
const palette = {poi:'#294f38',address:'#ae5429',area:'#75846c'};
const keywords=['面','火锅','烧烤','粉','海鲜','小吃','鱼','咖啡','甜品','牛肉'];
let saved;
try {saved=new Set(JSON.parse(localStorage.getItem('flavor-atlas-favorites-v1')||'[]'));} catch {saved=new Set();}
const s={city:'wuhan',data:null,sel:null,fav:false,mapped:false,tag:'',pos:null,locHint:'',q:'',district:'',sort:'personal',plimit:12,vlimit:12,visible:[],films:[],links:new Map(),view:null,cityLoad:0,showStreet:false,streetToken:0,emptyNote:'',mapUnit:null,manual:null,approx:false,locToken:0};
let streetMap=null,markerLayer=null,leafletPromise;
const norm=v=>String(v??'').trim().toLocaleLowerCase();
const regionName=()=>cities[s.city].name;
const hasPoint=p=>['poi','address','area'].includes(p.precision)&&Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&Math.abs(p.lat)<=85&&Math.abs(p.lon)<=180;
const precise=p=>hasPoint(p)&&p.precision!=='area';
const key=p=>s.city+'|'+p.name+'|'+p.address;
const tokens=v=>norm(v).split(/\s+/).filter(Boolean);
const allWords=(text,words)=>words.every(w=>text.includes(w));
const safeUrl=v=>{try{let u=new URL(v);return ['https:','http:'].includes(u.protocol)?u.href:null;}catch{return null;}};
function tag(name,cls,val){const el=document.createElement(name);if(cls)el.className=cls;if(val!==undefined)el.textContent=String(val);return el;}
function link(title,url){const href=safeUrl(url);if(!href)return tag('span','',title);const a=tag('a','',title);a.href=href;a.target='_blank';a.rel='noopener noreferrer';return a;}
function btn(text,fn,cls){const b=tag('button',cls,text);b.type='button';b.addEventListener('click',fn);return b;}
function pressed(b,yes){b.setAttribute('aria-pressed',String(yes));}
function message(container,text){container.replaceChildren(tag('p','empty',text));}
function scrollToId(id){$(id).scrollIntoView({block:'start',behavior:'instant'});}
function radians(d){return d*Math.PI/180;}
function km(a,b){const y=radians(b.lat-a.lat),x=radians(b.lon-a.lon), h=Math.sin(y/2)**2+Math.cos(radians(a.lat))*Math.cos(radians(b.lat))*Math.sin(x/2)**2;return 6371.0088*2*Math.asin(Math.sqrt(Math.min(1,Math.max(0,h))));}
function origin(){return s.manual||s.pos;}
function originName(){return s.manual?s.manual.name:'设备位置';}
function distance(p){const from=origin();return from&&hasPoint(p)&&(precise(p)||s.approx)?km(from,p):Infinity;}
function distanceTier(p){return !Number.isFinite(distance(p))?2:p.precision==='area'?1:0;}
function distText(p){
 const v=distance(p);if(!Number.isFinite(v))return '';const ref=!!(s.manual?.precision==='area'||p.precision==='area');
 const label=ref?'片区参考直线约 ':p.precision==='address'?'地址参考直线约 ':'直线约 ';
 return label+(v<1?(Math.round(v*1000/10)*10)+' 米':v.toFixed(v<20?1:0)+' 公里');
}
function textPlace(p){
 const titles=p.videos.filter(v=>!videoCaution(v)&&s.links.get(v.bvid)?.size===1&&(v.namedPlaces?.length||0)<=1).map(v=>v.title);
 return norm([p.name,p.address,p.district,...titles].join(' '));
}
function videoCaution(video) {
 if(video.stance==='historical_closure') return '原片提到停业，当前状态请复核';
 if(video.stance==='negative') return '作者在该期表达保留意见';
 if(video.stance==='mixed') return '作者在该期提到优点和不足';
 const title=String(video.title||'').replace(/(?:包不会|不会|没有|没|不容易|避免)踩雷/g,'');
 return /踩雷篇|踩雷了|我踩雷|大踩雷|不推荐|太难吃|再也不[来去]|劝退|失望/u.test(title)?'标题提示有保留意见':'';
}
function rankPlace(p,words){
 const neutral=p.videos.filter(v=>!videoCaution(v));const mixed=p.videos.some(v=>v.stance==='mixed');
 const caution=p.videos.length>0&&!neutral.length&&!mixed;
 const hits=[...new Set(words)].filter(w=>p._text.includes(w));const v=distance(p);
 const geo=Number.isFinite(v)&&precise(p)&&s.manual?.precision!=='area'?(v<=1?5:v<=3?3:v<=8?2:v<=15?1:0):0;
 const verified=hasPoint(p)?({poi:3,address:2,area:1}[p.precision]||0):0;
 const score=4*Math.min(2,hits.length)+geo+verified+Number(neutral.length>0)-(caution?8:0);
 const why=[];
 if(caution)why.push('关联标题有保留意见，请先看原片');
 if(mixed&&!neutral.length)why.push('该店的原片评价有褒有贬');
 if(hits.length&&!caution)why.push('匹配「'+hits.slice(0,2).join('、')+'」');
 if(geo)why.push('距'+originName()+' '+distText(p));
 if(why.length<2&&verified)why.push(p.precision==='poi'?'有可核对的店铺点位':p.precision==='address'?'已记录可核地址':'有片区参考点');
 if(why.length<2&&neutral.length)why.push('可回看关联探店原片');
 if(!why.length)why.push('店址待核，可先查看探店记录');
 return {score,why:why.slice(0,2)};
}
function geoText(){
 if(s.manual){const approx=s.manual.precision==='area'?' 该起点为片区参考，距离可能偏离门店入口，误差范围未实测。':'';return [s.locHint,'当前按手选起点「'+s.manual.name+'」估算直线距离。',approx].filter(Boolean).join(' ');}
 if(!s.pos)return s.locHint||'可使用设备位置，也可选择本城店铺或地标作出发点。';
 const cityKm=km(s.pos,cities[s.city]);let base=cityKm>80?'设备位置距'+regionName()+'市中心参考点约 '+Math.round(cityKm)+' 公里。可改选本城出发点。':'已使用设备位置作出发点。';
 return base+(s.pos.accuracy?' 设备报告精度约 '+Math.round(s.pos.accuracy)+' 米。':'')+' 距离仅为直线估算。';
}
function selectOrigin(p){
 s.locToken++;$('locate').disabled=false;s.manual=p;s.locHint='';$('origin').value=p?String(p._i):'';s.sort=origin()?'near':'personal';$('sort').value=s.sort;
 if(p&&!s.data.places.some(precise)){s.approx=true;$('approx').checked=true;}s.sel=null;recompute();
}
function resetStreet(){s.streetToken++;s.showStreet=false;s.emptyNote='';if(streetMap){streetMap.remove();streetMap=null;markerLayer=null;}$('street').hidden=true;$('plot').hidden=false;pressed($('online'),false);$('online').textContent='街道底图';}
function resetFilters(){s.q='';s.district='';s.tag='';s.fav=false;s.mapped=false;s.plimit=12;s.vlimit=12;$('search').value='';$('district').value='';}
async function changeCity(id){
 if(!cities[id])return;const n=++s.cityLoad;resetStreet();s.city=id;s.manual=null;s.approx=false;$('approx').checked=false;$('origin').replaceChildren(new Option('选择本城店铺或地标…',''));s.data=null;s.sel=null;s.view=null;s.visible=[];s.films=[];resetFilters();s.sort='personal';$('sort').value=s.sort;
 document.querySelectorAll('[data-city]').forEach(b=>pressed(b,b.dataset.city===id));$('channel').textContent='正在打开'+regionName()+'档案…';$('district').replaceChildren(new Option('全部区域',''));$('tags').replaceChildren();$('placecount').textContent='';$('videocount').textContent='';$('mapname').textContent=regionName()+'点位图';$('detail').replaceChildren();$('places').replaceChildren();$('videos').replaceChildren();$('coverage').textContent='';$('location').textContent=geoText();$('moreplaces').hidden=true;$('morevideos').hidden=true;drawPlot();
 try{
 const response=await fetch('./data/'+id+'.json');if(!response.ok)throw new Error('HTTP '+response.status);const d=await response.json();if(n!==s.cityLoad)return;if(!Array.isArray(d.places)||!Array.isArray(d.catalog))throw new Error('目录格式不正确');s.data=d;
 const catalogById=new Map(d.catalog.map(video=>[video.bvid,video]));
 s.links=new Map();d.places.forEach((p,i)=>{p._i=i;p.videos=(p.videos||[]).map(video=>catalogById.get(video.bvid)||video);for(const v of p.videos){if(!s.links.has(v.bvid))s.links.set(v.bvid,new Set());s.links.get(v.bvid).add(p);}});
 for(const p of d.places)p._text=textPlace(p);
 for(const p of d.places.filter(hasPoint).sort((a,b)=>Number(!precise(a))-Number(!precise(b))||a.name.localeCompare(b.name,'zh-CN')))$('origin').add(new Option(p.name+' · '+(precision[p.precision]||'参考点'),String(p._i)));
 const creator=d.up?.name||'作者';$('channel').replaceChildren(tag('span','','探店 UP 主'),link(creator+' ↗',d.up?.url));for(const item of [...new Set(d.places.map(p=>p.district).filter(Boolean))].sort((a,b)=>a.localeCompare(b,'zh-CN')))$('district').add(new Option(item,item));
 const cv=d.coverage||{},day=cv.snapshotDate||cv.asOf;
 const pubCount=Number(cv.reportedTotal),limited=cv.catalogComplete===false;
 const coverageLabel=limited?'已核 '+d.catalog.length+' 条视频'+(Number.isFinite(pubCount)&&pubCount>0?' / 账号投稿 '+pubCount+' 条':''):'视频快照 '+(day||'');
 $('channel').append(tag('span','coverage-badge',coverageLabel));
 $('coverage').textContent=[day?'本城资料快照：'+day+'。':'',cv.coordinateNote,cv.statusNote,cv.note].filter(x=>typeof x==='string').join(' ');recompute();
 }catch(err){if(n!==s.cityLoad)return;$('channel').textContent=regionName()+'目录暂未载入';message($('places'),'读取城市快照失败。请通过项目的本地启动入口打开，并重试切换城市。');message($('videos'),'该城市的视频快照未加载。');}
}
function filterFilms(v,placeSet,words){
 const rel=s.links.get(v.bvid)||new Set(),restricted=s.district||s.fav||s.mapped;
 if(restricted&&![...rel].some(p=>placeSet.has(p._i)))return false;
 const txt=norm([v.title,v.bvid,...(v.namedPlaces||[]),...[...rel].map(p=>[p.name,p.address,p.district].join(' '))].join(' '));
 return allWords(txt,words);
}
function recompute(resetView=true){
 s.group=null;if(!s.data)return;const words=[...tokens(s.q),...tokens(s.tag)];s.visible=s.data.places.filter(p=>allWords(p._text,words)&&(!s.district||s.district===p.district)&&(!s.fav||saved.has(key(p)))&&(!s.mapped||hasPoint(p)));
 for(const p of s.visible)p._rank=rankPlace(p,words);
 if(s.sort==='personal')s.visible.sort((a,b)=>b._rank.score-a._rank.score||a._i-b._i);
 if(s.sort==='near')s.visible.sort((a,b)=>distanceTier(a)-distanceTier(b)||(distance(a)-distance(b))||a._i-b._i);
 if(s.sort==='videos')s.visible.sort((a,b)=>new Set(b.videos.map(v=>v.bvid)).size-new Set(a.videos.map(v=>v.bvid)).size||a._i-b._i);
 const ids=new Set(s.visible.map(p=>p._i));s.films=s.data.catalog.filter(v=>filterFilms(v,ids,words));
 if(!s.sel||!ids.has(s.sel._i))s.sel=s.visible[0]||null;
 if(resetView)s.view=null;
 const geo=s.visible.filter(hasPoint).length;$('placecount').textContent=s.visible.length+' 家店铺 · '+geo+' 处有坐标';$('videocount').textContent=s.films.length+' 条视频';
 $('location').textContent=geoText();pressed($('onlyfav'),s.fav);pressed($('onlymap'),s.mapped);
 renderTags();renderCards();renderDetail();renderFilms();drawMap(resetView);
}
function renderTags(){
 const titles=s.data.catalog.map(v=>norm(v.title));const frag=document.createDocumentFragment();
 keywords.filter(w=>s.data.places.some(p=>p._text.includes(w))||titles.some(t=>t.includes(w))).slice(0,8).forEach(w=>{const b=btn('# '+w,()=>{s.tag=s.tag===w?'':w;s.plimit=s.vlimit=12;recompute();});pressed(b,s.tag===w);frag.append(b);});$('tags').replaceChildren(frag);
}
function choose(p,scroll=false,group=null){
 if(!p)return;if(!s.visible.includes(p)){resetFilters();recompute();}
 s.sel=p;s.group=group;renderCards();renderDetail();if(hasPoint(p)&&s.view&&!inside(p,s.view))s.view=centerOn(p,s.view,.9);
 drawMap(false);if(streetMap&&hasPoint(p))streetMap.panTo([p.lat,p.lon]);if(scroll)scrollToId('atlas');
}
function renderCards(){const el=$('places');el.replaceChildren();
 for(const [i,p] of s.visible.slice(0,s.plimit).entries()){const b=btn('',()=>choose(p,true),'place');pressed(b,p===s.sel);b.append(tag('span','num',String(i+1).padStart(2,'0')));let t=tag('span');t.append(tag('span','place-name',p.name),tag('span','meta',[p.district||regionName(),precision[p.precision]||'坐标待核',distText(p)].filter(Boolean).join(' · ')));t.append(tag('span','reason',p._rank.why.join(' · ')));b.append(t);el.append(b);}
 if(!s.visible.length)message(el,s.data.places.length?'当前条件下没有店铺。可以更换关键词、取消筛选，或浏览下方视频。':'本城还没有完成地址核验的店铺，可先从下方视频目录浏览。');$('moreplaces').hidden=s.plimit>=s.visible.length;
}
function renderDetail(){const el=$('detail'),p=s.sel;el.replaceChildren();if(!p){el.append(tag('span','detail-type','本城档案'),tag('h3','','从视频出发'),tag('p','','当前没有可展示的店铺。视频目录保留原始标题、作者及原片链接。'));return;}
 el.append(tag('span','detail-type',[p.district||regionName(),precision[p.precision]||'坐标待核'].join(' / ')),tag('h3','',p.name),tag('p','',p.address||'地址待核，请查看原视频与作者说明。'));
 if(hasPoint(p))el.append(tag('p','',(distText(p)?'距'+originName()+' · '+distText(p):'')||(p.precision==='area'?'片区示意，不代表店铺入口。':p.lat.toFixed(4)+'° N · '+p.lon.toFixed(4)+'° E')));
 if(s.sort==='personal')el.append(tag('p','detailsub','排序依据：'+p._rank.why.join('；')));
 if(p.note)el.append(tag('p','',p.note));
 if(hasPoint(p))el.append(btn(s.manual===p?'当前手选起点':'用此'+(p.precision==='area'?'片区参考点':'店铺点位')+'作出发点',()=>selectOrigin(p)));
 for(const [k,label] of [['addressSource','核对门牌来源 ↗'],['coordinateSource','核对参考坐标 ↗']])if(safeUrl(p[k]))el.append(link(label,p[k]));
 if(p.source){const line=tag('p');if(safeUrl(p.source))line.append(link('查看收录依据 ↗',p.source));else line.textContent='收录依据：'+p.source;el.append(line);}
 if(s.group&&s.group.length>1){const same=tag('label','detailsub','该图点内的店铺 '),choices=tag('select','group-choice');for(const item of s.group)choices.add(new Option(item.name,String(item._i),false,item===p));choices.addEventListener('change',()=>choose(s.data.places[Number(choices.value)],false,s.group));same.append(choices);el.append(same);}
 if(p.videos.length){el.append(tag('p','detailsub','关联原视频 · '+p.videos.length));for(const v of p.videos){el.append(link(v.title+' ↗',v.url));const advisory=videoCaution(v);if(advisory)el.append(tag('span','meta',advisory));}}
 const fav=btn(saved.has(key(p))?'★ 已收藏':'☆ 收藏这家店',()=>{const k=key(p);if(saved.has(k))saved.delete(k);else saved.add(k);try{localStorage.setItem('flavor-atlas-favorites-v1',JSON.stringify([...saved]));}catch{}recompute(false);});pressed(fav,saved.has(key(p)));el.append(fav);
}
function renderFilms(){const el=$('videos');el.replaceChildren();for(const v of s.films.slice(0,s.vlimit)){
 const card=tag('article','film'),h=tag('h3');h.append(link(v.title+' ↗',v.url));const date=String(v.published??'').slice(0,10);card.append(tag('span','meta',[date,v.bvid].filter(Boolean).join(' / ')),h);
 const advisory=videoCaution(v);if(advisory)card.append(tag('span','meta',advisory));
 const related=[...(s.links.get(v.bvid)||[])];const row=tag('div','related');for(const p of related)row.append(btn(p.name+' ↗',()=>choose(p,true)));
 if(!related.length){const names=(v.namedPlaces||[]).join('、');row.append(tag('span','meta',(names?'原片提及 '+names:'作者投稿')+' · 未纳入本城店铺'));}card.append(row);el.append(card);}
 if(!s.films.length)message(el,'当前条件下没有匹配的视频。');$('morevideos').hidden=s.vlimit>=s.films.length;
}
function bounds(points){
 if(!points.length){let c=cities[s.city];return {west:c.lon-.12,east:c.lon+.12,south:c.lat-.08,north:c.lat+.08};}
 let west=180,east=-180,south=90,north=-90;for(const p of points){west=Math.min(west,p.lon);east=Math.max(east,p.lon);south=Math.min(south,p.lat);north=Math.max(north,p.lat);}
 const midx=(east+west)/2,midy=(north+south)/2,dy=Math.max(.018,(north-south)*1.2),dx=Math.max(.028,(east-west)*1.2,dy*1.65/Math.cos(radians(midy))),height=Math.max(dy,dx*Math.cos(radians(midy))/1.65);return {west:midx-dx/2,east:midx+dx/2,south:midy-height/2,north:midy+height/2};
}
function inside(p,b){return p.lon>=b.west&&p.lon<=b.east&&p.lat>=b.south&&p.lat<=b.north;}
function centerOn(p,b,factor){const w=Math.max(.0015,Math.min(40,(b.east-b.west)*factor))/2,h=Math.max(.001,Math.min(25,(b.north-b.south)*factor))/2;return {west:p.lon-w,east:p.lon+w,south:p.lat-h,north:p.lat+h};}
function svg(name,attrs,text){const el=document.createElementNS('http://www.w3.org/2000/svg',name);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);if(text!==undefined)el.textContent=text;return el;}
function addHydrography(plot,b,x,y,points){
 const layers=window.FOOD_ATLAS_RIVERS?.[s.city]||[];
 if(s.city==='wuhan'&&b.east-b.west<.12)return false;
 const clip=svg('clipPath',{id:'water-clip'});clip.append(svg('rect',{x:12,y:9,width:616,height:304}));const defs=svg('defs',{});defs.append(clip);plot.append(defs);
 const group=svg('g',{'clip-path':'url(#water-clip)','pointer-events':'none','aria-label':'公开来源的河流中心线'}),labels=[];
 for(const layer of layers){
  const coords=layer.lines.map(line=>line.map(([lon,lat])=>[x(lon),y(lat)]));
  const path=coords.map(line=>line.map(([px,py],i)=>(i?'L':'M')+px.toFixed(1)+' '+py.toFixed(1)).join(' ')).join(' ');
  const w=layer.weight===1?5.5:layer.weight===2?3.5:1.8;
  group.append(svg('path',{class:'river-line',d:path,stroke:'#a7c8c6','stroke-width':w+1.8,'stroke-linecap':'round','stroke-linejoin':'round',fill:'none'}),svg('path',{d:path,stroke:layer.weight===3?'#95b9b7':'#85b3b3','stroke-width':w,'stroke-linecap':'round','stroke-linejoin':'round',fill:'none'}));
  const candidates=[];const labelWidth=layer.name.length*10;
  for(const line of coords){for(let i=1;i<line.length;i++){
   const [a1,a2]=line[i-1],[b1,b2]=line[i];for(const t of [0,.25,.5,.75]){const px=a1+(b1-a1)*t,py=a2+(b2-a2)*t-6;if(px<30+labelWidth/2||px>606-labelWidth/2||py<30||py>265)continue;
    if(labels.some(v=>Math.abs(v[0]-px)<(v[2]+labelWidth)/2+10&&Math.abs(v[1]-py)<16))continue;
    let gap=40;for(const place of points){const xx=x(place.lon),yy=y(place.lat);gap=Math.min(gap,Math.hypot((xx-px)*.6,yy-py));}
    candidates.push([gap-.028*Math.abs(px-315)-.018*Math.abs(py-150),px,py]);
   }
  }}
  if(candidates.length){const [,px,py]=candidates.sort((a,b)=>b[0]-a[0])[0];labels.push([px,py,labelWidth,layer.name]);}
 }
 for(const [px,py,,name] of labels)group.append(svg('text',{class:'river-label',x:px,y:py,'text-anchor':'middle','font-size':12,'font-weight':650,fill:'#33696a',stroke:'#e7eddd','stroke-width':3,'paint-order':'stroke'},name));
 plot.append(group);return layers.length>0;
}
function hydroCredit(hasLayer){
 const label=origin()?'蓝圈：出发点 · ':'';
 const n=$('mapnote');n.replaceChildren(document.createTextNode(label+'离线图 · '));
 if(s.city==='wuhan'){if(!hasLayer)n.append(document.createTextNode('高倍视野隐藏概化河线 · '));n.append(link('Natural Earth','https://www.naturalearthdata.com/downloads/10m-physical-vectors/10m-rivers-lake-centerlines/'));}
 else n.append(link('© OpenStreetMap contributors','https://www.openstreetmap.org/copyright'),document.createTextNode(' · '),link('ODbL','https://opendatacommons.org/licenses/odbl/1-0/'));
}
function drawPlot(){
 const plot=$('plot'),points=s.visible.filter(hasPoint);plot.replaceChildren();let included=points;
 if(s.city==='fuzhou'&&s.data&&points.length&&s.visible.length===s.data.places.length)included=[...points,{lon:119.22,lat:26.008},{lon:119.365,lat:26.102}];
 const b=s.view||bounds(included);s.mapUnit=b;const x=v=>22+(v-b.west)/(b.east-b.west)*594,y=v=>310-(v-b.south)/(b.north-b.south)*285;
 for(let i=0;i<7;i++){const cx=22+i*99;plot.append(svg('line',{x1:cx,y1:15,x2:cx,y2:315,stroke:'#c6d2bd','stroke-dasharray':'2 4'}));if(i%2===0)plot.append(svg('text',{x:cx===616?570:cx,y:328,fill:'#5f6b5e','font-size':10},(b.west+(b.east-b.west)*i/6).toFixed(3)+'° E'));}
 for(let i=0;i<5;i++){const cy=25+i*71;plot.append(svg('line',{x1:18,y1:cy,x2:616,y2:cy,stroke:'#c6d2bd','stroke-dasharray':'2 4'}));}
 const hydro=addHydrography(plot,b,x,y,points);
 plot.append(svg('text',{x:607,y:19,fill:'#526b54','text-anchor':'end','font-size':11},'↑ 北'));
 const midLat=(b.south+b.north)/2,kmPerPixel=(b.east-b.west)*111.32*Math.cos(radians(midLat))/594;
 const scale=[.05,.1,.25,.5,1,2,5,10,20,50,100,200,500].filter(d=>d/kmPerPixel<=85).at(-1);
 if(scale){const end=35+scale/kmPerPixel;plot.append(svg('path',{d:'M35 282v5H'+end+'v-5',fill:'none',stroke:'#526b54','stroke-width':1.5}),svg('text',{x:35,y:278,fill:'#526b54','font-size':10},scale<1?(scale*1000)+' 米':scale+' 公里'));}
 const districts=new Map();for(const p of points){if(!p.district||!inside(p,b))continue;const group=districts.get(p.district)||[];group.push(p);districts.set(p.district,group);}
 const used=[];for(const [name,pts] of [...districts].sort((a,b)=>b[1].length-a[1].length)){
 const avg={lon:pts.reduce((n,p)=>n+p.lon,0)/pts.length,lat:pts.reduce((n,p)=>n+p.lat,0)/pts.length},xx=x(avg.lon)+9,yy=y(avg.lat)-12;
 if(used.some(([px,py])=>Math.abs(xx-px)<52&&Math.abs(yy-py)<19)||xx>585||yy<18||used.length>=8)continue;
 used.push([xx,yy]);const label=svg('text',{x:xx,y:yy,fill:'#435d42',stroke:'#e8ecd9','stroke-width':3,'paint-order':'stroke','font-size':11},name);label.append(svg('title',{},'按本区已收录点位计算的标签位置'));plot.append(label);
 }
 const bins=new Map();for(const p of points){if(!inside(p,b))continue;const px=x(p.lon),py=y(p.lat),k=Math.floor(px/15)+','+Math.floor(py/15);if(!bins.has(k))bins.set(k,[]);bins.get(k).push(p);}
 function mark(arr,p,active){const xx=x(p.lon),yy=y(p.lat),cluster=arr.length>1;const g=svg('g',{class:'marker',tabindex:0,role:'button','aria-label':cluster?arr.length+' 家店铺，放大查看':p.name,transform:'translate('+xx+','+yy+')'});g.append(svg('title',{},cluster?arr.map(i=>i.name).slice(0,5).join('、'):p.name));g.append(svg('circle',{r:active?10:cluster?8:5.5,fill:active?'#a83b20':cluster?'#344f3c':palette[p.precision],stroke:active?'#fff5c8':'#f7f6e6','stroke-width':active?2.5:1.5}));if(cluster)g.append(svg('text',{'text-anchor':'middle',y:3,fill:'white','font-size':8},arr.length));else if(active)g.append(svg('circle',{r:2.5,fill:'white'}));
 const hit=()=>{if(cluster){s.view=centerOn(p,b,.48);choose(p,false,arr);}else choose(p);};g.addEventListener('click',hit);g.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();hit();}});plot.append(g);}
 let activeBin=null;for(const arr of bins.values()){if(arr.includes(s.sel))activeBin=arr;else mark(arr,arr[0],false);}if(activeBin)mark(activeBin,s.sel,true);const ref=origin();if(ref&&inside(ref,b)){const c=svg('circle',{cx:x(ref.lon),cy:y(ref.lat),r:12,fill:'none',stroke:'#286e98','stroke-width':2,'pointer-events':'none'});c.append(svg('title',{},'出发点：'+originName()));plot.append(c);}
 $('mapempty').hidden=!!points.length&&!s.emptyNote;$('mapempty').textContent=s.emptyNote||'当前筛选没有可绘制的坐标。';hydroCredit(hydro);
}
function drawMap(fit=true){if(s.showStreet&&streetMap){markerLayer.clearLayers();const pts=s.visible.filter(hasPoint);for(const p of pts){const selected=p===s.sel;const m=window.L.circleMarker([p.lat,p.lon],{radius:selected?9:5,color:'#fff9df',weight:selected?3:1,fillColor:selected?'#a83b20':palette[p.precision],fillOpacity:.95}).addTo(markerLayer);m.bindTooltip(tag('span','',p.name));m.on('click',()=>choose(p));}if(origin())window.L.circleMarker([origin().lat,origin().lon],{radius:12,color:'#286e98',weight:2,fill:false,interactive:false}).addTo(markerLayer);if(fit){if(pts.length>1)streetMap.fitBounds(pts.map(p=>[p.lat,p.lon]),{padding:[16,16],maxZoom:15});else streetMap.setView(pts.length?[pts[0].lat,pts[0].lon]:[cities[s.city].lat,cities[s.city].lon],12);}$('mapempty').hidden=!!pts.length;$('mapempty').textContent='当前没有已核坐标。';$('mapnote').textContent='联网街道底图 · WGS84';}else drawPlot();}
function loadLeaflet(){if(window.L)return Promise.resolve();if(!leafletPromise){leafletPromise=new Promise((resolve,reject)=>{if(!document.querySelector('link[data-leaflet]')){const l=tag('link');l.rel='stylesheet';l.href='./vendor/leaflet/leaflet.css';l.dataset.leaflet='';document.head.append(l);}const e=tag('script');e.src='./vendor/leaflet/leaflet.js';e.onload=resolve;e.onerror=()=>{leafletPromise=null;reject(new Error('地图组件不可用'));};document.head.append(e);});}return leafletPromise;}
async function toggleStreet(){if(!s.data)return;if(s.showStreet){resetStreet();drawPlot();return;}const token=++s.streetToken;
 try{await loadLeaflet();if(token!==s.streetToken)return;s.showStreet=true;s.emptyNote='';$('plot').hidden=true;$('street').hidden=false;pressed($('online'),true);$('online').textContent='离线点位图';streetMap=window.L.map($('street'),{zoomControl:false,scrollWheelZoom:false,maxZoom:18});markerLayer=window.L.layerGroup().addTo(streetMap);
 let ok=0,failed=0;const tile=window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'});tile.on('tileload',()=>ok++);tile.on('tileerror',()=>failed++);tile.on('load',()=>{if(!ok&&failed)setTimeout(()=>{if(token!==s.streetToken||ok)return;resetStreet();drawPlot();$('location').textContent=(geoText()+' 街道底图未能联网，已恢复离线坐标图。').trim();},0);});tile.addTo(streetMap);drawMap(true);
 }catch{if(token===s.streetToken){resetStreet();drawPlot();$('location').textContent=(geoText()+' 街道底图不可用，已恢复离线坐标图。').trim();}}
}
function zoom(factor){if(!s.data)return;if(streetMap){factor<1?streetMap.zoomIn():streetMap.zoomOut();return;}const b=s.mapUnit||bounds([]);const target=s.sel&&precise(s.sel)&&inside(s.sel,b)?s.sel:{lat:(b.south+b.north)/2,lon:(b.west+b.east)/2};s.view=centerOn(target,b,factor);drawPlot();}
function locate(){
 if(!navigator.geolocation){s.locHint='当前浏览器不支持定位，可按城市或区域浏览。';$('location').textContent=s.locHint;return;}
 const token=++s.locToken;$('locate').disabled=true;$('location').textContent='正在请求设备位置…';navigator.geolocation.getCurrentPosition(pos=>{if(token!==s.locToken)return;s.manual=null;$('origin').value='';s.pos={lat:pos.coords.latitude,lon:pos.coords.longitude,accuracy:pos.coords.accuracy};s.locHint='';$('locate').disabled=false;$('locate').textContent='◎ 更新位置';s.sort='near';$('sort').value='near';s.sel=null;recompute();},error=>{if(token!==s.locToken)return;$('locate').disabled=false;s.locHint=error.code===1?'未获得定位权限，可手选本城出发点。':error.code===3?'定位超时，请重试或按区域浏览。':'未取得当前位置，可继续按区域浏览。';$('location').textContent=geoText();if(!origin()&&s.sort==='near'){s.sort='personal';$('sort').value='personal';recompute();}},{enableHighAccuracy:false,timeout:9500,maximumAge:120000});
}
document.querySelectorAll('[data-city]').forEach(b=>b.onclick=()=>{
 const id=b.dataset.city,url=new URL(location.href);url.searchParams.set('city',id);
 history.replaceState(null,'',url);changeCity(id);
});
$('search').oninput=e=>{s.q=e.target.value;s.plimit=s.vlimit=12;recompute();};$('district').onchange=e=>{s.district=e.target.value;s.plimit=s.vlimit=12;recompute();};$('sort').onchange=e=>{if(e.target.value==='near'&&!origin()){e.target.value=s.sort;locate();return;}s.sort=e.target.value;s.sel=null;recompute();};
$('onlymap').onclick=()=>{s.mapped=!s.mapped;recompute();};$('onlyfav').onclick=()=>{s.fav=!s.fav;recompute();};$('moreplaces').onclick=()=>{s.plimit+=24;renderCards();};$('morevideos').onclick=()=>{s.vlimit+=24;renderFilms();};$('locate').onclick=locate;$('online').onclick=toggleStreet;$('zoomin').onclick=()=>zoom(.5);$('zoomout').onclick=()=>zoom(2);$('resetview').onclick=()=>{s.view=null;drawMap(true);};
window.addEventListener('food-atlas:show-place',event=>{
 const d=event.detail;if(!d||!s.data||![s.city,regionName()].includes(d.city))return;
 const p=s.data.places.find(row=>row.name===d.name&&row.address===d.address);if(!p)return;
 resetFilters();s.sel=p;recompute();choose(p,true);
});
$('origin').onchange=e=>selectOrigin(e.target.value===''?null:s.data?.places[Number(e.target.value)]);$('approx').onchange=e=>{s.approx=e.target.checked;recompute();};
changeCity(new URLSearchParams(location.search).get('city')==='fuzhou'?'fuzhou':'wuhan');
