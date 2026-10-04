// Read-only ASCII view. Knows buttons, not policies, emulators, scores or timers.
(function (root) {
  function snapshot(buttons) {
    if (!Array.isArray(buttons)) return {frame:'[ CONTROLLER INPUT UNKNOWN ]', fire:false, direction:'unknown'};
    const held=new Set(buttons), dx=Number(held.has(7))-Number(held.has(6)), dy=Number(held.has(5))-Number(held.has(4));
    const direction=[dy<0?'up':dy>0?'down':'',dx<0?'left':dx>0?'right':''].filter(Boolean).join('-')||'center';
    const grid=Array.from({length:3},()=>Array(7).fill(' '));
    grid[1+dy][3+dx*2]='O';
    if(dy<=0)grid[2][3]=dx<0?'\\':dx>0?'/':'|';
    const fire=held.has(0), button=fire?'(@@@)':'(   )';
    const frame=['      ATARI JOYSTICK',...grid.map(row=>'               '+row.join('')),
      '.------------------------.', '| '+button+'          [___] |', "'------------------------'"].join('\n');
    return {frame,fire,direction,button};
  }
  function render(element,buttons,{proposed=null,reason=null,stale=false}={}) {
    const value=snapshot(stale?null:buttons);element.replaceChildren();
    const parts=value.button?value.frame.split(value.button):[value.frame];
    element.append(document.createTextNode(parts[0]));
    if(value.button){const b=document.createElement('span');b.textContent=value.button;b.style.color=value.fire?'#ff4141':'#bd5555';b.style.fontWeight='bold';element.append(b,document.createTextNode(parts[1]));}
    element.append(document.createTextNode('\nHELD: '+value.direction+(value.fire?' + FIRE':'')+'\n'+(proposed?'Last proposed: '+proposed:'No proposal yet')+(reason?' · '+reason:'')+'\nHeld inputs are not proof of sprite movement.'));
    element.setAttribute('aria-label','Atari controller: '+value.direction+(value.fire?', fire held':''));
    return value;
  }
  const api={snapshot,render};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.AtariController=api;
})(typeof window==='undefined'?globalThis:window);
