/* Local video notes. Match source records without sending notes or location. */
(() => {
  'use strict';
  const root = document.getElementById('video-import');
  if (!root) return;
  const key = 'food-atlas:reviewed-notes:1';
  let ticket = 0;
  const snapshots = new Map();
  function element(type, text) {
    const node = document.createElement(type);
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function input(label, control) {
    const block = element('label', label);
    block.append(control);
    return block;
  }
  function getNotes() {
    try { const notes = JSON.parse(localStorage.getItem(key)); return Array.isArray(notes) ? notes : []; }
    catch { return []; }
  }
  function parseBV(raw) {
    const bv = /^(BV[1-9A-HJ-NP-Za-km-z]{10})$/;
    if (bv.test(raw.trim())) return raw.trim();
    try {
      const url = new URL(raw.trim());
      if (!['www.bilibili.com','m.bilibili.com','bilibili.com'].includes(url.hostname) ||
          !['https:', 'http:'].includes(url.protocol)) return '';
      return url.pathname.match(/^\/video\/(BV[1-9A-HJ-NP-Za-km-z]{10})\/?$/)?.[1] || '';
    } catch { return ''; }
  }
  const fold = element('details');
  fold.className = 'note-panel';
  fold.append(element('summary', '核对一条探店视频'));
  const help = element('p', '粘贴 BV 号或 B 站视频链接，可选填简介中的店名和地址。核对结果保存在当前浏览器。');
  const form = element('form');
  const url = element('input');
  url.required = true; url.maxLength = 600; url.placeholder = 'BV 号或 bilibili.com/video/…';
  const excerpt = element('textarea');
  excerpt.rows = 2; excerpt.maxLength = 500; excerpt.placeholder = '例如：店名、分店、所在街道';
  const submit = element('button','核对来源与店址'); submit.type = 'submit';
  const result = element('div');
  result.setAttribute('aria-live','polite');
  const history = element('div');
  form.append(input('视频链接',url),input('店址线索（选填）',excerpt),submit);
  fold.append(help,form,result,history);
  root.append(fold);
  function city() {
    return document.querySelector('[data-city][aria-pressed="true"]')?.dataset.city || 'wuhan';
  }
  function showPlace(city, p) {
    window.dispatchEvent(new CustomEvent('food-atlas:show-place',{detail:{city,name:p.name,address:p.address}}));
  }
  function showHistory() {
    history.replaceChildren();
    const notes = getNotes().filter(n => n.city === city());
    if (!notes.length) return;
    history.append(element('h3','我的复核记录'));
    const list = element('ul');
    for (const n of notes) {
      const li=element('li');
      const source=element('a',n.title || n.bvid); source.href='https://www.bilibili.com/video/'+encodeURIComponent(n.bvid)+'/';
      source.target='_blank'; source.rel='noopener noreferrer';
      const remove=element('button','移除');
      remove.type='button';
      remove.onclick=()=>{try{localStorage.setItem(key,JSON.stringify(getNotes().filter(x=>!(x.city===n.city&&x.bvid===n.bvid))));showHistory();}catch{result.textContent='浏览器无法修改本地记录。';}};
      li.append(source,document.createTextNode(' · '+n.decision+' '),remove);
      list.append(li);
    }
    history.append(list);
  }
  async function snapshot(id) {
    if (!snapshots.has(id)) {
      const response=await fetch('./data/'+id+'.json');
      if (!response.ok) throw new Error('目录读取失败');
      snapshots.set(id,await response.json());
    }
    return snapshots.get(id);
  }
  form.onsubmit=async event=>{
    event.preventDefault();
    const id=city(), run=++ticket, bvid=parseBV(url.value);
    result.replaceChildren();
    if (!bvid) {result.textContent='请使用完整 BV 号或原视频链接。短链接可先打开，再复制原视频地址。';return;}
    try {
      const data=await snapshot(id);
      if(run!==ticket||id!==city())return;
      const video=data.catalog.find(v=>v.bvid===bvid);
      const hint=excerpt.value.trim().toLowerCase();
      const known=data.places.filter(p=>p.videos.some(v=>v.bvid===bvid));
      let matches=known;
      if (!known.length && hint) {
        matches=data.places.filter(p=>p.name.length>=2 && hint.includes(p.name.toLowerCase()));
      }
      result.append(element('p',video?'已在「'+data.up.name+'」投稿快照中核对：'+video.title:'当前作者快照未收录这个 BV 号，作者与城市归属待核。'));
      const choices=element('select');
      choices.add(new Option('保留待核，不添加地图坐标',''));
      for(const [i,p] of matches.entries()) choices.add(new Option(p.name+' · '+(p.address||'地址待核'),String(i)));
      if(known.length===1)choices.value='0';
      result.append(element('p',known.length?'以下店铺已有同一原视频的关联记录。':matches.length?'以下是线索中出现的现有店名，请对照分店和门牌后决定。':'尚无足够店址证据，可以先保存为待核线索。'));
      result.append(input('复核结论',choices));
      const save=element('button','保存到我的复核记录');save.type='button';
      save.onclick=()=>{
        const place=choices.value===''?null:matches[Number(choices.value)];
        const decision=place?place.name+'（'+(known.includes(place)?'快照已关联':'本人选择，待独立核验')+'）':'待核店址';
        const notes=getNotes().filter(n=>!(n.city===id&&n.bvid===bvid));
        notes.unshift({city:id,bvid,title:video?.title||bvid,decision,hint});
        try{localStorage.setItem(key,JSON.stringify(notes));showHistory();save.textContent='已保存在本机';}
        catch{save.textContent='保存失败，请检查浏览器存储';}
      };
      result.append(save);
      if(known.length){const locate=element('button','在本城列表查看');locate.type='button';
        locate.onclick=()=>{if(choices.value!=='')showPlace(id,matches[Number(choices.value)]);else choices.focus();};result.append(locate);}
    } catch {if(run===ticket)result.textContent='未能读取城市目录，请通过本机启动入口打开后重试。';}
  };
  for(const b of document.querySelectorAll('[data-city]')) b.addEventListener('click',()=>{
    ++ticket;result.replaceChildren();url.value='';excerpt.value='';queueMicrotask(showHistory);
  });
  showHistory();
})();
