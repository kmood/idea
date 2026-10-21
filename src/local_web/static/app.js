const labels={source:'来源',trend:'趋势',idea:'点子'};
const state={records:[],meta:{},query:'',kind:'idea',evidence:'',researchStatus:'',accessStatus:'',compareIds:new Set()};
const list=document.querySelector('#record-list');
const empty=document.querySelector('#empty');
const errorBox=document.querySelector('#error');
const dialog=document.querySelector('#detail');
const detail=document.querySelector('#detail-content');
const comparePanel=document.querySelector('#compare-panel');
const compareList=document.querySelector('#compare-list');

function filtered(){
  const query=state.query.trim().toLocaleLowerCase('zh-CN');
  return state.records.filter(record=>{
    const haystack=[record.id,record.title,record.summary,record.marketOrSource,record.evidence,record.status].filter(Boolean).join(' ').toLocaleLowerCase('zh-CN');
    return (!query||haystack.includes(query))&&(!state.kind||record.kind===state.kind)&&(!state.evidence||(record.evidence||'').includes(state.evidence))&&(!state.researchStatus||(record.kind==='idea'&&record.researchStatus===state.researchStatus))&&(!state.accessStatus||(record.kind==='source'&&record.accessStatus===state.accessStatus));
  });
}

function text(tag,className,value){const node=document.createElement(tag);if(className)node.className=className;node.textContent=value;return node;}

function render(){
  const records=filtered();list.replaceChildren();
  records.forEach(record=>{
    const row=document.createElement('div');row.className='record-row';
    if(record.kind==='idea'){
      const label=document.createElement('label');label.className='compare-toggle';
      const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=state.compareIds.has(record.id);checkbox.disabled=!checkbox.checked&&state.compareIds.size>=3;checkbox.setAttribute('aria-label',`选择比较：${record.title}`);
      checkbox.addEventListener('change',()=>{if(checkbox.checked)state.compareIds.add(record.id);else state.compareIds.delete(record.id);render();});
      label.append(checkbox,text('span','compare-toggle-text','比较'));row.append(label);
    }
    const button=document.createElement('button');button.type='button';button.className='record';button.dataset.kind=record.kind;button.dataset.id=record.id;
    const top=document.createElement('span');top.className='record-top';top.append(text('span','kind',labels[record.kind]),text('span','record-id',record.id));
    const title=text('strong','record-title',record.title);
    const summary=text('span','record-summary',record.summary||'暂无说明');
    const meta=document.createElement('span');meta.className='record-meta';
    [record.marketOrSource,record.fit,record.evidenceLevel||record.evidence,record.researchStatus||record.accessStatus,record.updatedAt].filter(Boolean).forEach(value=>meta.append(text('span','tag',value)));
    if(record.evidenceNote)meta.append(text('span','tag',record.evidenceNote));
    button.append(top,title,summary,meta);button.addEventListener('click',()=>openDetail(record));row.append(button);list.append(row);
  });
  renderCompare();
  list.setAttribute('aria-busy','false');empty.hidden=records.length!==0;
  document.querySelector('#result-count').textContent=`显示 ${records.length} / ${state.records.length} 条`;
}

function renderCompare(){
  const selected=state.records.filter(record=>record.kind==='idea'&&state.compareIds.has(record.id));
  comparePanel.hidden=selected.length===0;compareList.replaceChildren();
  selected.forEach(record=>{
    const card=document.createElement('article');card.className='compare-card';
    card.append(text('strong','compare-card-title',record.title),text('span','tag',record.researchStatus||'未知状态'),text('span','tag',record.evidence||'证据未知'),text('p','compare-card-summary',record.summary||'暂无摘要'));
    const remove=document.createElement('button');remove.type='button';remove.className='compare-remove';remove.textContent='移出比较';remove.addEventListener('click',()=>{state.compareIds.delete(record.id);render();});card.append(remove);compareList.append(card);
  });
}

async function openDetail(record){
  detail.replaceChildren(text('p','loading','正在读取详情…'));dialog.showModal();
  try{
    const response=await fetch(`/api/documents/${encodeURIComponent(record.kind)}/${encodeURIComponent(record.id)}`);
    if(!response.ok)throw new Error('detail');
    const document=await response.json();detail.innerHTML=document.html;
    const heading=detail.querySelector('h1');if(heading)heading.tabIndex=-1;(heading||dialog.querySelector('.close')).focus();
  }catch{detail.replaceChildren(text('p','error-message','详情读取失败，请稍后重试。'));}
}

document.querySelector('#search').addEventListener('input',event=>{state.query=event.target.value;render();});
document.querySelectorAll('input[name="kind"]').forEach(input=>input.addEventListener('change',event=>{
  state.kind=event.target.value;
  if(state.kind==='idea')state.accessStatus='';
  if(state.kind==='source')state.researchStatus='';
  document.querySelector('#research-status').value=state.researchStatus;
  document.querySelector('#access-status').value=state.accessStatus;
  updateFilterAvailability();render();
}));
document.querySelector('#evidence').addEventListener('change',event=>{state.evidence=event.target.value;render();});
document.querySelector('#research-status').addEventListener('change',event=>{state.researchStatus=event.target.value;render();});
document.querySelector('#access-status').addEventListener('change',event=>{state.accessStatus=event.target.value;render();});
document.querySelector('#reset').addEventListener('click',()=>{state.query='';state.kind='';state.evidence='';state.researchStatus='';state.accessStatus='';state.compareIds.clear();document.querySelector('#search').value='';document.querySelector('input[name="kind"][value=""]').checked=true;document.querySelector('#evidence').value='';document.querySelector('#research-status').value='';document.querySelector('#access-status').value='';render();});
dialog.querySelector('.close').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});

function setOptions(selector,values,emptyLabel){const element=document.querySelector(selector);element.replaceChildren(new Option(emptyLabel,''),...values.map(value=>new Option(value,value)));}
function updateFilterAvailability(){
  document.querySelector('#research-status').disabled=state.kind==='source';
  document.querySelector('#access-status').disabled=state.kind==='idea';
}
function statusSummary(counts){return ['待验证','候选','搁置'].filter(value=>counts[value]).map(value=>`${value} ${counts[value]}`).join(' · ')||'暂无状态统计';}
function applyCatalog(catalog){
  state.records=catalog.records;state.meta=catalog.meta;state.compareIds=new Set([...state.compareIds].filter(id=>state.records.some(record=>record.kind==='idea'&&record.id===id)));document.querySelector('#phase').textContent=catalog.meta.phase||'未知';
  Object.entries(catalog.meta.counts).forEach(([kind,count])=>document.querySelector(`#${kind}-count`).textContent=count);
  document.querySelector('#selected-count').textContent=catalog.meta.selectedCount??0;
  document.querySelector('#source-hostname-count').textContent=`不同 hostname ${catalog.meta.sourceMetrics.hostnameCount}`;
  document.querySelector('#idea-status-counts').textContent=statusSummary(catalog.meta.statusCounts.idea||{});
  const researchOptions=catalog.meta.filters.ideaResearchStatus||[];const accessOptions=catalog.meta.filters.sourceAccessStatus||[];
  if(state.researchStatus&&!researchOptions.includes(state.researchStatus))state.researchStatus='';
  if(state.accessStatus&&!accessOptions.includes(state.accessStatus))state.accessStatus='';
  setOptions('#research-status',researchOptions,'全部点子状态');document.querySelector('#research-status').value=state.researchStatus;
  setOptions('#access-status',accessOptions,'全部来源状态');document.querySelector('#access-status').value=state.accessStatus;
  updateFilterAvailability();render();
}
async function refreshCatalog(){
  const button=document.querySelector('#refresh');const status=document.querySelector('#refresh-status');button.disabled=true;status.textContent='读取中…';
  try{const response=await fetch('/api/catalog',{cache:'no-store'});if(!response.ok)throw new Error('catalog');applyCatalog(await response.json());status.textContent='已刷新';}
  catch{status.textContent=state.records.length?'刷新失败，保留当前资料':'资料读取失败';if(!state.records.length){list.hidden=true;errorBox.hidden=false;document.querySelector('#result-count').textContent='读取失败';}}
  finally{button.disabled=false;}
}
document.querySelector('#refresh').addEventListener('click',refreshCatalog);
document.querySelector('#check-consistency').addEventListener('click',async()=>{
  const status=document.querySelector('#refresh-status');status.textContent='检查中…';
  try{const response=await fetch('/api/consistency',{cache:'no-store'});if(!response.ok)throw new Error('consistency');const result=await response.json();status.textContent=result.ok?`资料检查通过${result.warnings.length?`，${result.warnings.length} 个警告`:''}`:`发现 ${result.errors.length} 个错误`;}
  catch{status.textContent='检查失败';}
});
refreshCatalog().catch(()=>{});
