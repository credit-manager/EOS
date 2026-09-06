const $=id=>document.getElementById(id);
async function load(){
  const r=await fetch('/api/v1/industry/packs');
  if(!r.ok){$('status').textContent='Sign in to use EOS';return;}
  const body=await r.json(); const packs=body.packs||[];
  $('status').textContent=`${packs.length} industry packs`;
  const list=$('entities'); list.innerHTML='';
  packs.forEach(pack=>{const button=document.createElement('button');button.type='button';button.textContent=pack.display_name;button.onclick=()=>selectPack(pack);list.appendChild(button)});
}
async function selectPack(pack){
  $('empty').textContent=`${pack.display_name} (${pack.version}) is available. Install it from the authenticated administration API.`;
}
load().catch(()=>{$('status').textContent='Service unavailable'});