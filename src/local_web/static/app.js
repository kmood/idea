const labels={source:'来源',trend:'趋势',idea:'点子'};
const state={records:[],query:'',kind:'',evidence:'',status:''};
const list=document.querySelector('#record-list');
const empty=document.querySelector('#empty');
const errorBox=document.querySelector('#error');
const dialog=document.querySelector('#detail');
const detail=document.querySelector('#detail-content');

function filtered(){
  const query=state.query.trim().toLocaleLowerCase('zh-CN');
  return state.records.filter(record=>{
    const haystack=[record.id,record.title,record.summary,record.marketOrSource,record.evidence,record.status].filter(Boolean).join(' ').toLocaleLowerCase('zh-CN');
    return (!query||haystack.includes(query))&&(!state.kind||record.kind===state.kind)&&(!state.evidence||(record.evidence||'').includes(state.evidence))&&(!state.status||(record.status||'').includes(state.status));
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
    [record.marketOrSource,record.evidence,record.status,record.updatedAt].filter(Boolean).forEach(value=>meta.append(text('span','tag',value)));
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
document.querySelectorAll('input[name="kind"]').forEach(input=>input.addEventListener('change',event=>{state.kind=event.target.value;render();}));
document.querySelector('#evidence').addEventListener('change',event=>{state.evidence=event.target.value;render();});
document.querySelector('#status').addEventListener('change',event=>{state.status=event.target.value;render();});
document.querySelector('#reset').addEventListener('click',()=>{state.query='';state.kind='';state.evidence='';state.status='';document.querySelector('#search').value='';document.querySelector('input[name="kind"][value=""]').checked=true;document.querySelector('#evidence').value='';document.querySelector('#status').value='';render();});
dialog.querySelector('.close').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{if(event.target===dialog)dialog.close();});

fetch('/api/catalog').then(response=>{if(!response.ok)throw new Error('catalog');return response.json();}).then(catalog=>{
  state.records=catalog.records;document.querySelector('#phase').textContent=catalog.meta.phase||'未知';
  Object.entries(catalog.meta.counts).forEach(([kind,count])=>document.querySelector(`#${kind}-count`).textContent=count);
  render();
}).catch(()=>{list.hidden=true;errorBox.hidden=false;document.querySelector('#result-count').textContent='读取失败';});
