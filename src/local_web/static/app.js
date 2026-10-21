const labels={source:'来源',trend:'趋势',idea:'点子'};
const state={records:[],meta:{},query:'',kind:'',evidence:'',researchStatus:'',accessStatus:''};
const list=document.querySelector('#record-list');
const empty=document.querySelector('#empty');
const errorBox=document.querySelector('#error');
const dialog=document.querySelector('#detail');
const detail=document.querySelector('#detail-content');

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
    const button=document.createElement('button');button.type='button';button.className='record';button.dataset.kind=record.kind;button.dataset.id=record.id;
    const top=document.createElement('span');top.className='record-top';top.append(text('span','kind',labels[record.kind]),text('span','record-id',record.id));
    const title=text('strong','record-title',record.title);
    const summary=text('span','record-summary',record.summary||'暂无说明');
    const meta=document.createElement('span');meta.className='record-meta';
    [record.marketOrSource,record.evidence,record.researchStatus||record.accessStatus,record.updatedAt].filter(Boolean).forEach(value=>meta.append(text('span','tag',value)));
    if(record.evidenceNote)meta.append(text('span','tag',record.evidenceNote));
    button.append(top,title,summary,meta);button.addEventListener('click',()=>openDetail(record));list.append(button);
  });
  list.setAttribute('aria-busy','false');empty.hidden=records.length!==0;
  document.querySelector('#result-count').textContent=`显示 ${records.length} / ${state.records.length} 条`;
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
document.querySelector('#reset').addEventListener('click',()=>{state.query='';state.kind='';state.evidence='';state.researchStatus='';state.accessStatus='';document.querySelector('#search').value='';document.querySelector('input[name="kind"][value=""]').checked=true;document.querySelector('#evidence').value='';document.querySelector('#research-status').value='';document.querySelector('#access-status').value='';render();});
dialog.querySelector('.close').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});

function setOptions(selector,values,emptyLabel){const element=document.querySelector(selector);element.replaceChildren(new Option(emptyLabel,''),...values.map(value=>new Option(value,value)));}
function updateFilterAvailability(){
  document.querySelector('#research-status').disabled=state.kind==='source';
  document.querySelector('#access-status').disabled=state.kind==='idea';
}
function statusSummary(counts){return ['待验证','候选','搁置'].filter(value=>counts[value]).map(value=>`${value} ${counts[value]}`).join(' · ')||'暂无状态统计';}

fetch('/api/catalog').then(response=>{if(!response.ok)throw new Error('catalog');return response.json();}).then(catalog=>{
  state.records=catalog.records;state.meta=catalog.meta;document.querySelector('#phase').textContent=catalog.meta.phase||'未知';
  Object.entries(catalog.meta.counts).forEach(([kind,count])=>document.querySelector(`#${kind}-count`).textContent=count);
  document.querySelector('#selected-count').textContent=catalog.meta.selectedCount??0;
  document.querySelector('#source-hostname-count').textContent=`不同 hostname ${catalog.meta.sourceMetrics.hostnameCount}`;
  document.querySelector('#idea-status-counts').textContent=statusSummary(catalog.meta.statusCounts.idea||{});
  setOptions('#research-status',catalog.meta.filters.ideaResearchStatus||[],'全部点子状态');
  setOptions('#access-status',catalog.meta.filters.sourceAccessStatus||[],'全部来源状态');
  updateFilterAvailability();render();
}).catch(()=>{list.hidden=true;errorBox.hidden=false;document.querySelector('#result-count').textContent='读取失败';});
