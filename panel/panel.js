(() => {
const $ = id => document.getElementById(id);
const C = {coral:'#ef3b2c',ink:'#333333',cream:'#f6ead2',stone:'#c9d0d2',stoneD:'#a7b1b4',orange:'#f9a51a',green:'#56b79d',greenD:'#3e8f7a',bronze:'#b0674a',bronzeD:'#8e4f37',white:'#fbf8f1',win:'#5a5f63'};
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;

/* ---------- landmarks (drawn at the size they have when R = 520) ---------- */
const svg = (w,h,body) => `<svg viewBox="0 0 ${w} ${h}" aria-hidden="true">${body}</svg>`;
const L = {
  eiffel:{w:78,h:235,label:'Eyfel Kulesi',draw:(w,h)=>svg(60,180,`
    <path fill-rule="evenodd" fill="${C.bronze}" d="M2 180 L22 92 L38 92 L58 180 Z M13 180 Q30 128 47 180 Z"/>
    <path fill="${C.bronzeD}" d="M30 92 L38 92 L58 180 L47 180 Q42 160 30 150 Z" opacity=".55"/>
    <rect x="8" y="128" width="44" height="6" rx="1" fill="${C.bronzeD}"/>
    <rect x="18" y="88" width="24" height="6" rx="1" fill="${C.bronzeD}"/>
    <path fill="${C.bronze}" d="M23 92 L27.5 34 L32.5 34 L37 92 Z"/>
    <path fill="${C.bronzeD}" d="M30 34 L32.5 34 L37 92 L30 92 Z" opacity=".55"/>
    <rect x="24" y="56" width="12" height="4" fill="${C.bronzeD}"/>
    <rect x="26" y="28" width="8" height="7" rx="1" fill="${C.bronzeD}"/>
    <rect x="29" y="6" width="2" height="23" fill="${C.bronzeD}"/>
    <g stroke="${C.cream}" stroke-width="1" opacity=".55"><path d="M10 160 L50 160 M15 146 L45 146 M24 110 L36 110 M25 74 L35 74 M26 44 L34 44"/><path d="M18 128 L27 92 M42 128 L33 92 M25 88 L30 60 M35 88 L30 60"/></g>`)},
  liberty:{w:84,h:225,label:'Özgürlük Heykeli',draw:()=>svg(60,160,`
    <rect x="8" y="104" width="44" height="56" fill="${C.cream}"/>
    <rect x="30" y="104" width="22" height="56" fill="#e6d6b8"/>
    <rect x="4" y="100" width="52" height="7" fill="${C.stoneD}"/>
    <rect x="14" y="116" width="6" height="12" rx="3" fill="${C.win}"/><rect x="27" y="116" width="6" height="12" rx="3" fill="${C.win}"/><rect x="40" y="116" width="6" height="12" rx="3" fill="${C.win}"/>
    <path fill="${C.green}" d="M18 100 L22 54 Q30 44 38 54 L42 100 Z"/>
    <path fill="${C.greenD}" d="M30 48 Q36 50 38 54 L42 100 L31 100 Z" opacity=".6"/>
    <path fill="${C.greenD}" d="M22 70 Q30 76 40 68" stroke="${C.greenD}" stroke-width="1.5" fill-opacity="0"/>
    <rect x="16" y="60" width="7" height="12" rx="1" transform="rotate(-12 19 66)" fill="${C.greenD}"/>
    <path fill="${C.green}" d="M34 52 L39 16 L43.5 17 L39 54 Z"/>
    <rect x="37.5" y="12" width="8" height="6" rx="1" fill="${C.greenD}"/>
    <path fill="${C.orange}" d="M41.5 2 Q47 8 44.5 12 L38.5 12 Q36 7 41.5 2 Z"/><path fill="${C.coral}" d="M41.5 6 Q44 9 42.8 12 L40 12 Q39 9 41.5 6 Z"/>
    <circle cx="29" cy="44" r="6" fill="${C.green}"/>
    <path fill="${C.green}" d="M21 40 L23 33 L26 38 L28 30 L30 37 L33 31 L34 38 L38 34 L37 41 Z"/>`)},
  pisa:{w:78,h:210,label:'Pisa Kulesi',draw:()=>svg(60,160,`
    <g transform="rotate(6 30 160)">
    <rect x="11" y="150" width="38" height="10" fill="${C.stoneD}"/>
    <rect x="13" y="30" width="34" height="122" fill="${C.white}"/>
    <rect x="33" y="30" width="14" height="122" fill="#ebe3d3"/>
    ${[0,1,2,3,4,5].map(i=>{const y=34+i*19;return `<rect x="11" y="${y+15}" width="38" height="3" fill="${C.stone}"/>${[0,1,2,3].map(k=>`<rect x="${16+k*7.5}" y="${y+2}" width="4.5" height="11" rx="2.2" fill="${C.stoneD}"/>`).join('')}`}).join('')}
    <rect x="17" y="12" width="26" height="20" fill="${C.white}"/>
    <rect x="31" y="12" width="12" height="20" fill="#ebe3d3"/>
    ${[0,1,2].map(k=>`<rect x="${20+k*7.5}" y="16" width="4.5" height="11" rx="2.2" fill="${C.stoneD}"/>`).join('')}
    <rect x="15" y="9" width="30" height="4" fill="${C.stone}"/>
    <rect x="15" y="28" width="30" height="3" fill="${C.stone}"/></g>`)},
  bigben:{w:62,h:240,label:'Big Ben',draw:()=>svg(44,170,`
    <rect x="8" y="58" width="28" height="112" fill="#e8c88c"/>
    <rect x="24" y="58" width="12" height="112" fill="#d7b273"/>
    ${[0,1,2,3,4].map(i=>`<rect x="13" y="${90+i*16}" width="4" height="10" fill="${C.win}"/><rect x="27" y="${90+i*16}" width="4" height="10" fill="#7a6a55"/>`).join('')}
    <rect x="5" y="44" width="34" height="34" fill="${C.cream}"/>
    <circle cx="22" cy="61" r="12" fill="#fff" stroke="${C.ink}" stroke-width="1.5"/>
    <path d="M22 61 L22 52 M22 61 L28 64" stroke="${C.ink}" stroke-width="1.6" stroke-linecap="round"/>
    <rect x="9" y="28" width="26" height="17" fill="#e8c88c"/>
    <rect x="14" y="31" width="5" height="11" rx="2.5" fill="${C.win}"/><rect x="25" y="31" width="5" height="11" rx="2.5" fill="${C.win}"/>
    <path d="M6 29 L22 2 L38 29 Z" fill="#3f6d5f"/><path d="M22 2 L38 29 L22 29 Z" fill="#2f574b"/>
    <rect x="21.3" y="0" width="1.4" height="4" fill="${C.ink}"/>`)},
  galata:{w:66,h:200,label:'Galata Kulesi',draw:()=>svg(50,150,`
    <rect x="8" y="52" width="34" height="98" fill="#e2d6bf"/>
    <rect x="27" y="52" width="15" height="98" fill="#cfc1a6"/>
    ${[0,1,2,3].map(i=>`<rect x="14" y="${66+i*20}" width="5" height="10" rx="2.5" fill="${C.win}"/><rect x="30" y="${66+i*20}" width="5" height="10" rx="2.5" fill="#6d6458"/>`).join('')}
    <rect x="11" y="128" width="9" height="22" rx="4.5" fill="#6d6458"/>
    <rect x="4" y="44" width="42" height="7" fill="${C.cream}"/>
    ${[0,1,2,3,4,5,6].map(k=>`<rect x="${6+k*6}" y="38" width="1.6" height="7" fill="${C.ink}"/>`).join('')}
    <rect x="4" y="37" width="42" height="2" fill="${C.ink}"/>
    <rect x="10" y="26" width="30" height="12" fill="${C.cream}"/>
    ${[0,1,2,3].map(k=>`<rect x="${13+k*7}" y="28" width="4" height="8" rx="2" fill="${C.win}"/>`).join('')}
    <path d="M6 28 L25 0 L44 28 Z" fill="#56678a"/><path d="M25 0 L44 28 L25 28 Z" fill="#455574"/>`)},
  windmill:{w:100,h:180,label:'Hollanda yel değirmeni',draw:()=>svg(70,130,`
    <path d="M20 130 L26 50 L44 50 L50 130 Z" fill="${C.coral}"/>
    <path d="M35 50 L44 50 L50 130 L35 130 Z" fill="#d22f22"/>
    <rect x="30" y="108" width="10" height="22" rx="5" fill="${C.cream}"/>
    <rect x="31" y="74" width="8" height="10" rx="1" fill="#fff" stroke="${C.win}" stroke-width="1"/>
    <path d="M22 54 L35 36 L48 54 Z" fill="${C.ink}"/>
    <g class="blades">${[0,90,180,270].map(r=>`<g transform="rotate(${r} 35 46)"><rect x="33.5" y="4" width="3" height="42" fill="${C.cream}"/><rect x="36.5" y="6" width="9" height="34" fill="none" stroke="${C.cream}" stroke-width="1.5"/><path d="M36.5 14 H45.5 M36.5 22 H45.5 M36.5 30 H45.5" stroke="${C.cream}" stroke-width="1"/></g>`).join('')}<circle cx="35" cy="46" r="3" fill="${C.ink}"/></g>`)},
  taj:{w:190,h:160,label:'Tac Mahal',draw:()=>svg(110,92,`
    <rect x="0" y="82" width="110" height="10" fill="${C.cream}"/>
    ${[4,100].map(x=>`<rect x="${x}" y="34" width="6" height="48" fill="${C.white}"/><rect x="${x+3}" y="34" width="3" height="48" fill="#e7e0d2"/><path d="M${x-1} 35 Q${x+3} 26 ${x+7} 35 Z" fill="${C.white}"/><rect x="${x+2.6}" y="24" width="0.8" height="4" fill="${C.ink}"/>`).join('')}
    <rect x="24" y="46" width="62" height="36" fill="${C.white}"/>
    <rect x="58" y="46" width="28" height="36" fill="#ebe4d6"/>
    <path d="M47 82 V62 Q55 52 63 62 V82 Z" fill="#c3ccd3"/>
    <path d="M30 82 V70 Q34 65 38 70 V82 Z M72 82 V70 Q76 65 80 70 V82 Z M30 62 V56 Q34 52 38 56 V62 Z M72 62 V56 Q76 52 80 56 V62 Z" fill="#c3ccd3"/>
    <path d="M38 46 Q34 20 55 10 Q76 20 72 46 Z" fill="${C.white}"/>
    <path d="M55 10 Q76 20 72 46 L55 46 Z" fill="#ebe4d6"/>
    <rect x="54.4" y="2" width="1.2" height="9" fill="${C.ink}"/>
    ${[28,76].map(x=>`<path d="M${x} 47 Q${x} 36 ${x+3} 34 Q${x+6} 36 ${x+6} 47 Z" fill="${C.white}"/>`).join('')}`)},
  pyramids:{w:200,h:118,label:'Gize Piramitleri',draw:()=>svg(120,70,`
    <path d="M10 70 L55 8 L100 70 Z" fill="#f4bd57"/><path d="M55 8 L100 70 L66 70 Z" fill="#dc9a35"/>
    <path d="M78 70 L98 42 L118 70 Z" fill="#f4bd57"/><path d="M98 42 L118 70 L104 70 Z" fill="#dc9a35"/>
    <path d="M0 70 L12 54 L24 70 Z" fill="#f4bd57"/><path d="M12 54 L24 70 L15 70 Z" fill="#dc9a35"/>
    <g stroke="#e8a845" stroke-width=".8" opacity=".7"><path d="M44 24 H66 M36 36 H74 M28 48 H82 M20 60 H90"/></g>`)},
  pagoda:{w:80,h:205,label:'Japon pagodası',draw:()=>svg(60,150,`
    ${[0,1,2,3].map(i=>{const y=128-i*28, s=1-i*0.13, bw=36*s, x=30-bw/2;return `<rect x="${x}" y="${y}" width="${bw}" height="22" fill="${C.coral}"/><rect x="${30}" y="${y}" width="${bw/2}" height="22" fill="#d22f22"/><rect x="${x+bw*0.3}" y="${y+6}" width="${bw*0.4}" height="10" fill="${C.cream}"/><path d="M${x-10} ${y+2} Q30 ${y-12} ${x+bw+10} ${y+2} L${x+bw+4} ${y+4} L${x-4} ${y+4} Z" fill="#3b3b44"/>`}).join('')}
    <rect x="29" y="20" width="2" height="26" fill="#3b3b44"/>${[0,1,2,3].map(k=>`<rect x="26" y="${24+k*5}" width="8" height="1.6" fill="#3b3b44"/>`).join('')}`)},
  opera:{w:205,h:96,label:'Sidney Opera Binası',draw:()=>svg(130,60,`
    <rect x="0" y="50" width="130" height="10" fill="${C.cream}"/><rect x="0" y="50" width="130" height="2" fill="#e0cfae"/>
    ${[[14,46,8,30],[40,74,6,28],[66,100,10,26],[92,124,18,24]].map(([a,b,t,c])=>`<path d="M${a} 50 Q${a+4} ${t+8} ${b} ${t} Q${b-8} ${t+18} ${b-4} 50 Z" fill="${C.white}" stroke="#c8cfd4" stroke-width="1"/><path d="M${b-4} 50 Q${b-8} ${t+18} ${b} ${t} Q${b-2} ${t+22} ${b+2} 50 Z" fill="#dfe4e8"/>`).join('')}`)},
  burj:{w:52,h:310,label:'Burj Halife',draw:()=>svg(40,220,`
    <path d="M4 220 L7 168 L11 168 L13 116 L16 116 L17.5 62 L19.2 0 L20.8 0 L22.5 62 L24 116 L27 116 L29 168 L33 168 L36 220 Z" fill="#c4ced6"/>
    <path d="M20 0 L20.8 0 L22.5 62 L24 116 L27 116 L29 168 L33 168 L36 220 L20 220 Z" fill="#a5b2bd"/>
    <g stroke="#e9eef2" stroke-width=".8" opacity=".8">${Array.from({length:18},(_,i)=>`<path d="M${8+i*0.2} ${210-i*11} H${32-i*0.6}"/>`).join('')}</g>`)},
  brandenburg:{w:165,h:118,label:'Brandenburg Kapısı',draw:()=>svg(100,72,`
    <rect x="2" y="66" width="96" height="6" fill="${C.stoneD}"/>
    <rect x="4" y="24" width="92" height="9" fill="${C.cream}"/>
    <path d="M30 24 L50 12 L70 24 Z" fill="${C.cream}"/>
    ${[6,22,38,56,72,88].map(x=>`<rect x="${x}" y="33" width="6" height="33" fill="${C.white}"/><rect x="${x+3.5}" y="33" width="2.5" height="33" fill="#ddd4c2"/>`).join('')}
    <rect x="4" y="31" width="92" height="2" fill="${C.stone}"/>
    <path d="M43 12 L44 5 L47 7 L49 3 L52 7 L55 4 L57 10 L57 12 Z" fill="#4a7d6b"/>`)},
  christ:{w:110,h:175,label:'Kurtarıcı İsa Heykeli',draw:()=>svg(80,128,`
    <path d="M0 128 Q14 92 30 88 Q42 84 52 90 Q70 100 80 128 Z" fill="#7cc06b"/><path d="M40 86 Q60 92 80 128 L46 128 Z" fill="#62a654"/>
    <rect x="35" y="78" width="10" height="12" fill="${C.cream}"/>
    <path d="M36 80 L37 40 L43 40 L44 80 Z" fill="${C.white}"/>
    <path d="M8 40 L72 40 L72 45 L44 46 L36 46 L8 45 Z" fill="${C.white}"/>
    <path d="M40 40 L72 40 L72 45 L44 46 L44 80 L40 80 Z" fill="#e4ddcf"/>
    <circle cx="40" cy="35" r="4.5" fill="${C.white}"/>`)},
};

/* filler: Dutch canal houses, like the reference */
const HOUSE_COL = [C.coral,'#f2c14e',C.stone,C.orange,'#e9564a',C.stone,'#f7a64b'];
function house(i){
  const col = HOUSE_COL[i % HOUSE_COL.length], kind = ['step','bell','roof'][i%3];
  const w = 58 + (i*13)%26, h = 96 + (i*29)%66, g = 26;
  const shade = `rgba(0,0,0,.08)`;
  let top;
  if(kind==='step') top = `<path d="M0 ${h} V${g} H${w*.16} V${g-9} H${w*.32} V${g-18} H${w*.68} V${g-9} H${w*.84} V${g} H${w} V${h} Z" fill="${col}"/>`;
  else if(kind==='bell') top = `<path d="M0 ${h} V${g} Q0 ${g-12} ${w*.25} ${g-13} Q${w*.24} ${g-30} ${w*.5} ${g-34} Q${w*.76} ${g-30} ${w*.75} ${g-13} Q${w} ${g-12} ${w} ${g} V${h} Z" fill="${col}"/><circle cx="${w/2}" cy="${g-20}" r="4" fill="${C.cream}"/>`;
  else top = `<rect x="0" y="${g}" width="${w}" height="${h-g}" fill="${col}"/><path d="M-4 ${g+2} L${w/2} ${g-26} L${w+4} ${g+2} Z" fill="${C.coral==col?'#c9301f':C.coral}"/><path d="M${w/2} ${g-26} L${w+4} ${g+2} L${w/2} ${g+2} Z" fill="rgba(0,0,0,.12)"/>`;
  const rows = Math.max(2, Math.floor((h-g-24)/20)), cols = w>56?3:2, cw = (w-12)/cols;
  let wins='';
  for(let r=0;r<rows;r++) for(let c=0;c<cols;c++){
    const x=6+c*cw+cw*.18, y=g+6+r*20, ww=cw*.64;
    wins += `<rect x="${x}" y="${y}" width="${ww}" height="12" rx="${kind==='bell'?ww/2:1}" fill="#fff" stroke="${C.win}" stroke-width="1"/><path d="M${x+ww/2} ${y} V${y+12} M${x} ${y+6} H${x+ww}" stroke="${C.win}" stroke-width=".8"/>`;
  }
  const door = `<rect x="${w/2-6}" y="${h-18}" width="12" height="18" rx="6" fill="${C.ink}" opacity=".75"/><rect x="0" y="${h-22}" width="${w}" height="3" fill="${C.cream}"/>`;
  return {w, h, draw:()=>svg(w,h,`${top}<rect x="${w*.62}" y="${g}" width="${w*.38}" height="${h-g}" fill="${shade}"/>${wins}${door}`)};
}
const lamp = {w:12,h:70,draw:()=>svg(12,70,`<rect x="5" y="10" width="2" height="60" fill="#8a7563"/><rect x="2" y="2" width="8" height="10" rx="2" fill="${C.cream}" stroke="#8a7563" stroke-width="1.2"/>`)};
const tree = (i)=>({w:34,h:58+(i%3)*10,draw:function(){return svg(34,this.h,`<rect x="15" y="${this.h-22}" width="4" height="22" fill="#8a6a50"/><circle cx="17" cy="${this.h-34}" r="15" fill="#5fb878"/><circle cx="23" cy="${this.h-30}" r="9" fill="#4ea366"/>`)}});
const cloudSVG = `<svg viewBox="0 0 80 40" aria-hidden="true"><path d="M10 34 Q0 34 4 26 Q8 18 18 22 Q20 8 34 10 Q42 0 54 8 Q66 6 66 18 Q78 18 76 28 Q74 34 64 34 Z" fill="#eaf7fb"/><path d="M10 34 Q14 30 22 31 Q40 36 64 34 Z" fill="#d5ecf4"/></svg>`;

/* more landmarks */
Object.assign(L, {
  hagia:{w:200,h:140,label:'Ayasofya',draw:()=>svg(120,84,`
    ${[4,18,98,112].map(x=>`<rect x="${x}" y="14" width="4" height="70" fill="#ece4d6"/><path d="M${x-1} 15 L${x+2} 2 L${x+5} 15 Z" fill="#8796a8"/><rect x="${x-1}" y="40" width="6" height="2" fill="#d8cdb9"/>`).join('')}
    <rect x="24" y="50" width="72" height="34" fill="#e8b49b"/><rect x="60" y="50" width="36" height="34" fill="#d79e84"/>
    <path d="M26 52 Q34 38 46 52 Z M74 52 Q86 38 94 52 Z" fill="#93a6ba"/>
    <rect x="40" y="44" width="40" height="8" fill="#e8b49b"/>${[0,1,2,3,4].map(i=>`<rect x="${45+i*7}" y="46" width="2" height="4" fill="#7a5a4c"/>`).join('')}
    <path d="M38 46 Q60 12 82 46 Z" fill="#9fb2c5"/><path d="M60 13 Q82 18 82 46 L60 46 Z" fill="#8698ad"/>
    <rect x="59.4" y="6" width="1.2" height="8" fill="#c9962f"/>
    ${[0,1,2,3].map(i=>`<path d="M${33+i*15} 84 V72 Q${37+i*15} 66 ${41+i*15} 72 V84 Z" fill="#9c6a55"/>`).join('')}`)},
  maiden:{w:92,h:124,label:'Kız Kulesi',draw:()=>svg(60,82,`
    <path d="M0 82 Q4 70 14 68 L46 68 Q56 70 60 82 Z" fill="#9aa7b3"/><path d="M30 68 L46 68 Q56 70 60 82 L34 82 Z" fill="#87949f"/>
    <rect x="8" y="54" width="44" height="15" fill="#f1e6d3"/><rect x="30" y="54" width="22" height="15" fill="#e0d2ba"/>
    ${[12,20,38,45].map(x=>`<rect x="${x}" y="58" width="3" height="6" rx="1.5" fill="${C.win}"/>`).join('')}
    <rect x="22" y="26" width="14" height="30" fill="#f1e6d3"/><rect x="29" y="26" width="7" height="30" fill="#e0d2ba"/>
    <rect x="26" y="32" width="3" height="7" rx="1.5" fill="${C.win}"/><rect x="26" y="44" width="3" height="7" rx="1.5" fill="${C.win}"/>
    <rect x="20" y="23" width="18" height="4" fill="#d0c3ab"/>
    <rect x="25" y="15" width="8" height="9" fill="#f1e6d3"/><path d="M23 16 L29 5 L35 16 Z" fill="#8796a8"/>
    <rect x="28.5" y="1" width="1" height="5" fill="${C.ink}"/><path d="M29.5 1 L34 2.5 L29.5 4 Z" fill="${C.coral}"/>`)},
  colosseum:{w:190,h:100,label:'Kolezyum',draw:()=>svg(130,68,`
    <path d="M4 68 V20 Q50 12 86 14 L92 24 L100 18 L108 28 L118 26 L126 34 V68 Z" fill="#e6c79c"/>
    <path d="M86 14 L92 24 L100 18 L108 28 L118 26 L126 34 V68 L86 68 Z" fill="#d6b384"/>
    <rect x="4" y="60" width="122" height="8" fill="#d4b07f"/>
    <path d="M4 34 H126 M4 48 H126" stroke="#c9a676" stroke-width="2"/>
    ${[[50,10,0,126],[36,10,0,126],[22,9,0,84]].map(([y,h,x0,x1])=>{let s='';for(let x=x0+8;x+8<=x1;x+=12) s+=`<path d="M${x} ${y+h} V${y+3} Q${x+4} ${y-1} ${x+8} ${y+3} V${y+h} Z" fill="#a8835a"/>`;return s}).join('')}`)},
  sagrada:{w:120,h:230,label:'Sagrada Família',draw:()=>svg(70,135,`
    ${[[10,42,10],[24,16,11],[36,4,12],[48,20,11],[60,46,10]].map(([x,t,w])=>`<path d="M${x-w/2} 96 C${x-w/2} ${t+30} ${x-w*.25} ${t+6} ${x} ${t} C${x+w*.25} ${t+6} ${x+w/2} ${t+30} ${x+w/2} 96 Z" fill="#dcbd8f"/><path d="M${x} ${t} C${x+w*.25} ${t+6} ${x+w/2} ${t+30} ${x+w/2} 96 L${x} 96 Z" fill="#c9a774"/>${Array.from({length:Math.floor((90-t)/9)},(_,i)=>`<ellipse cx="${x}" cy="${t+14+i*9}" rx="1.4" ry="2.4" fill="#a88458"/>`).join('')}<circle cx="${x}" cy="${t}" r="2.6" fill="${x===36?C.orange:C.coral}"/>`).join('')}
    <rect x="4" y="92" width="62" height="43" fill="#d8b98c"/><rect x="35" y="92" width="31" height="43" fill="#c6a576"/>
    <circle cx="35" cy="106" r="7" fill="#c69a5c" stroke="#a88458" stroke-width="1.5"/>
    <path d="M28 135 V122 Q35 113 42 122 V135 Z" fill="#8e6a42"/>`)},
  basil:{w:130,h:160,label:'Aziz Vasil Katedrali',draw:()=>{
    const onion=(cx,by,w,h,c)=>`<rect x="${cx-w*.65}" y="${by}" width="${w*1.3}" height="${66-by}" fill="#f3e2c2"/><path d="M${cx-w} ${by} C${cx-w*1.5} ${by-h*.5} ${cx-w*.2} ${by-h*.7} ${cx} ${by-h} C${cx+w*.2} ${by-h*.7} ${cx+w*1.5} ${by-h*.5} ${cx+w} ${by} Z" fill="${c}"/><path d="M${cx-w*.9} ${by-h*.25} L${cx-w*.45} ${by-h*.4} L${cx} ${by-h*.25} L${cx+w*.45} ${by-h*.4} L${cx+w*.9} ${by-h*.25}" stroke="#fff" stroke-width="1.2" fill="none" opacity=".8"/><path d="M${cx} ${by-h} C${cx+w*.2} ${by-h*.7} ${cx+w*1.5} ${by-h*.5} ${cx+w} ${by} L${cx} ${by} Z" fill="rgba(0,0,0,.14)"/><rect x="${cx-.6}" y="${by-h-6}" width="1.2" height="7" fill="#c9962f"/>`;
    return svg(90,110,`<path d="M38 66 L45 8 L52 66 Z" fill="#e8a33c"/><path d="M45 8 L52 66 L45 66 Z" fill="#cf8a28"/>${onion(45,14,4,9,'#3f9a62')}
      ${onion(22,62,9,20,'#2f6fb8')}${onion(68,62,9,20,'#e0b53a')}${onion(32,50,7,16,'#3f9a62')}${onion(58,50,7,16,'#c9453a')}
      <rect x="10" y="66" width="70" height="44" fill="#c4473a"/><rect x="45" y="66" width="35" height="44" fill="#a93a2f"/>
      ${[16,28,52,64].map(x=>`<path d="M${x} 84 V76 Q${x+4} 71 ${x+8} 76 V84 Z" fill="#f3e2c2"/>`).join('')}
      <path d="M39 110 V96 Q45 89 51 96 V110 Z" fill="#5a2a22"/>`);}},
  londoneye:{w:150,h:165,label:'London Eye',draw:()=>svg(120,132,`
    <path d="M60 64 L36 130 M60 64 L84 130" stroke="#b9c3cb" stroke-width="4" stroke-linecap="round"/><rect x="30" y="128" width="60" height="4" fill="#9aa5ae"/>
    <g class="wheel"><circle cx="60" cy="62" r="52" fill="none" stroke="#f4f7f9" stroke-width="3"/><circle cx="60" cy="62" r="47" fill="none" stroke="#f4f7f9" stroke-width="1"/>
    ${Array.from({length:16},(_,i)=>{const a=i*Math.PI/8, x=60+52*Math.cos(a), y=62+52*Math.sin(a);return `<line x1="60" y1="62" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="#f4f7f9" stroke-width="1"/><ellipse cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" rx="4" ry="3" fill="#fff" stroke="#9aa5ae" stroke-width="1"/>`}).join('')}</g>
    <circle cx="60" cy="62" r="5" fill="#9aa5ae"/>`)},
  petronas:{w:100,h:270,label:'Petronas Kuleleri',draw:()=>{
    const tw=x=>`<path d="M${x-9} 180 V64 H${x-7} V48 H${x-5} V36 H${x-3} V28 L${x} 2 L${x+3} 28 V36 H${x+5} V48 H${x+7} V64 H${x+9} V180 Z" fill="#c4ced6"/><path d="M${x} 2 L${x+3} 28 V36 H${x+5} V48 H${x+7} V64 H${x+9} V180 H${x} Z" fill="#a5b2bd"/>${Array.from({length:13},(_,i)=>`<rect x="${x-8}" y="${70+i*8.5}" width="16" height="1" fill="#e9eef2" opacity=".8"/>`).join('')}`;
    return svg(64,180,`${tw(16)}${tw(48)}<rect x="24" y="96" width="16" height="4" fill="#8d99a3"/><path d="M25 100 L29 110 M39 100 L35 110" stroke="#8d99a3" stroke-width="1.5"/>`);}},
});
L.burj.h=270;

/* Estenove clinic */
const CLINIC={w:180,h:150,label:'Estenove kliniği',draw:()=>svg(180,150,`
  <rect x="6" y="46" width="168" height="104" fill="#fbfaf6"/><rect x="122" y="46" width="52" height="104" fill="#efece4"/>
  <rect x="2" y="40" width="176" height="8" fill="#032f6e"/>
  <rect x="50" y="36" width="3" height="5" fill="#032f6e"/><rect x="127" y="36" width="3" height="5" fill="#032f6e"/>
  <rect x="32" y="6" width="116" height="32" rx="9" fill="#032f6e"/>
  <text x="90" y="29" text-anchor="middle" font-family="Changa One, Arial Black, Arial, sans-serif" font-size="20" letter-spacing="1" fill="#ffffff">ESTENOVE</text>
  ${[16,48,104,136].map(x=>`<rect x="${x}" y="56" width="28" height="22" rx="2" fill="#cfe6ff" stroke="#032f6e" stroke-width="1.5"/><path d="M${x+5} ${73} L${x+13} ${61}" stroke="#fff" stroke-width="2" opacity=".8"/>`).join('')}
  <text x="90" y="91" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700" font-size="7.5" letter-spacing="1.4" fill="#032f6e">SAÇ EKİM KLİNİĞİ</text>
  <path d="M64 101 L116 101 L111 95 L69 95 Z" fill="#0462f2"/>
  <rect x="72" y="102" width="36" height="46" fill="#bfe0ff" stroke="#032f6e" stroke-width="2"/><path d="M90 102 V148" stroke="#032f6e" stroke-width="1.5"/>
  <rect x="85" y="122" width="2" height="8" fill="#032f6e"/><rect x="93" y="122" width="2" height="8" fill="#032f6e"/>
  <circle cx="34" cy="116" r="11" fill="#0462f2"/><path d="M34 110 V122 M28 116 H40" stroke="#fff" stroke-width="3.2" stroke-linecap="round"/>
  <rect x="126" y="100" width="40" height="32" rx="2" fill="#fff" stroke="#032f6e" stroke-width="1.5"/>
  <text x="136" y="108" text-anchor="middle" font-family="Arial" font-size="5" font-weight="700" fill="#032f6e">ÖNCE</text><text x="156" y="108" text-anchor="middle" font-family="Arial" font-size="5" font-weight="700" fill="#032f6e">SONRA</text>
  <circle cx="136" cy="120" r="6" fill="#f1c7a1"/><ellipse cx="134" cy="116.5" rx="2" ry="1" fill="#fff" opacity=".7"/><path d="M133.5 123.5 Q136 122 138.5 123.5" stroke="#5a3a2a" stroke-width=".8" fill="none"/>
  <circle cx="156" cy="120" r="6" fill="#f1c7a1"/><path d="M150 119 Q150 111.5 156 111.5 Q162 111.5 162 119 Q160 115 156 115.5 Q152 115 150 119 Z" fill="#3a2618"/><path d="M153.5 122.5 Q156 125 158.5 122.5" stroke="#5a3a2a" stroke-width=".8" fill="none"/>
  <circle cx="64" cy="146" r="7" fill="#5fb878"/><circle cx="116" cy="146" r="7" fill="#5fb878"/>
  <rect x="64" y="147" width="52" height="3" fill="#d9d2c3"/>`)};

/* walkers: bald and glum on the way in, a full head of hair and waving on the way out */
const SKIN=['#f1c7a1','#e3b08a','#c98e64','#a8714c','#f4d2b0'];
function personSVG(kind,i){
  const bald=kind==='bald', skin=SKIN[i%SKIN.length];
  const shirt=bald?['#8a96a3','#7d8794','#9aa3ad','#6f7b88','#858a8f'][i%5]:['#ef3b2c','#0b7bff','#f9a51a','#2fae7a','#d14fa0'][i%5];
  const hair=['#3a2618','#7a4a28','#1d1410','#b5652b','#d9a441'][i%5];
  const legs=`<g class="lg"><rect x="10" y="38" width="4.5" height="16" rx="2" fill="#3b4252"/><rect x="8.5" y="52" width="7" height="4.5" rx="2" fill="#222"/></g><g class="lg lg2"><rect x="15.5" y="38" width="4.5" height="16" rx="2" fill="#3b4252"/><rect x="14.5" y="52" width="7" height="4.5" rx="2" fill="#222"/></g>`;
  const body=`<rect x="7" y="22" width="16" height="19" rx="6" fill="${shirt}"/>`;
  const arms=bald
    ? `<rect x="4.5" y="24" width="4" height="13" rx="2" fill="${shirt}" transform="rotate(6 6.5 24)"/><rect x="21.5" y="24" width="4" height="13" rx="2" fill="${shirt}" transform="rotate(-6 23.5 24)"/>`
    : `<rect x="4.5" y="24" width="4" height="13" rx="2" fill="${shirt}" transform="rotate(10 6.5 24)"/><g class="wave"><rect x="21.5" y="12" width="4" height="13" rx="2" fill="${shirt}" transform="rotate(25 23.5 25)"/><circle cx="27.5" cy="12" r="2.4" fill="${skin}"/></g>`;
  const head=`<circle cx="15" cy="13" r="9" fill="${skin}"/>`;
  const face=bald
    ? `<ellipse cx="11.5" cy="7" rx="3.2" ry="1.8" fill="#fff" opacity=".6"/><path d="M10 11.2 L13 10 M20 11.2 L17 10" stroke="#5a3a2a" stroke-width="1" stroke-linecap="round"/><circle cx="12" cy="13.6" r="1" fill="#2a1d14"/><circle cx="18" cy="13.6" r="1" fill="#2a1d14"/><path d="M12 19 Q15 16.6 18 19" stroke="#5a3a2a" stroke-width="1.2" fill="none" stroke-linecap="round"/><path d="M19.4 15.2 q1.3 2 0 3 q-1.3 -1 0 -3 z" fill="#5fb3ff"/>`
    : `<path d="M5.5 14 Q3.5 2.5 15 2 Q26.5 2.5 24.5 14 Q23.5 7.5 18 7 Q14 10 9 7.6 Q6.5 9.5 5.5 14 Z" fill="${hair}"/><path d="M10.5 13 Q12 11.4 13.5 13 M16.5 13 Q18 11.4 19.5 13" stroke="#2a1d14" stroke-width="1.1" fill="none" stroke-linecap="round"/><circle cx="10.3" cy="16" r="1.6" fill="#f39a9a" opacity=".6"/><circle cx="19.7" cy="16" r="1.6" fill="#f39a9a" opacity=".6"/><path d="M11.5 17 Q15 21.6 18.5 17 Z" fill="#fff" stroke="#5a3a2a" stroke-width="1"/><path d="M3 4 l1 2.2 2.2 1 -2.2 1 -1 2.2 -1 -2.2 -2.2 -1 2.2 -1 z" fill="#fff"/>`;
  return svg(30,58,`<g class="bob">${legs}${body}${arms}${head}${face}</g>`);
}

/* ---------- state ---------- */
let R=500, u=1, phase='login', userName='';
const world=$('world'), spin=$('spin'), cloudspin=$('cloudspin'), globe=$('globe'), ringspin=$('ringspin'), clouddrift=$('clouddrift');
const DRIFT=3.2;            // degrees per second the planet keeps turning
let walkers=[], WALK={half:8,plaza:12}, drift=24;
const ROT_WELCOME=-100;
const narrow = () => innerWidth < 720;
const textAngle = () => narrow() ? -22 : -38;   // where the greeting lands on screen
const gapAngle = () => textAngle() - ROT_WELCOME;    // where it lives on the planet

function camera(p){
  const w=innerWidth, h=innerHeight;
  if(p==='login') return {x:w/2, y:h*.42+R, s:1, r:0};
  if(p==='welcome') return {x:w*(narrow()?.7:.7), y:h*(narrow()?.44:.40)+R*.85, s:.85, r:ROT_WELCOME};
  const s=16; return {x:w/2, y:h*.5+R*s*.82, s, r:ROT_WELCOME-12};
}
function applyCamera(instant){
  const c=camera(phase);
  if(instant){[world,spin,cloudspin].forEach(e=>e.style.transition='none')}
  world.style.transform=`translate(${c.x}px,${c.y}px) scale(${c.s})`;
  spin.style.transform=`rotate(${c.r}deg)`;
  cloudspin.style.transform=`rotate(${c.r*.55}deg)`;
  if(instant){requestAnimationFrame(()=>requestAnimationFrame(()=>[world,spin,cloudspin].forEach(e=>e.style.transition='')))}
}
function place(el,a,lift,anchorTop){
  el.style.transform=`rotate(${a}deg) translate(0px,${-R-lift}px) translate(-50%,${anchorTop?'0%':'-100%'})`;
}

function layout(){
  const w=innerWidth, h=innerHeight;
  R=Math.round(Math.max(h*.5, Math.min(w*.62, h*.62)));
  u=R/520;
  globe.style.cssText=`left:${-R}px;top:${-R}px;width:${2*R}px;height:${2*R}px`;
  ringspin.innerHTML=''; clouddrift.innerHTML=''; walkers=[];

  // one full ring: the clinic at 0°, landmarks clockwise round the planet, houses filling the gaps
  const deg = px => px/520*57.2958, PACK=.84;
  let hi=0, ti=0;
  const H=()=>house(hi++), T=()=>tree(ti++);
  const plaza=()=>({w:130,h:10,spacer:true});
  const marks=[L.liberty,L.bigben,L.galata,L.hagia,L.maiden,L.taj,L.windmill,L.pyramids,L.pagoda,L.opera,L.burj,L.petronas,L.londoneye,L.colosseum,L.sagrada,L.brandenburg,L.basil,L.christ,L.pisa,L.eiffel];
  const seq=[CLINIC,plaza(),lamp,...marks,lamp,plaza()];
  const wd=it=>it.spacer?deg(it.w):deg(it.w)*PACK;
  let total=seq.reduce((s,it)=>s+wd(it),0), k=0;
  while(k<200){
    const f=(k%3===2)?T():H();
    if(total+wd(f)>354) break;
    const m=marks[1+(k%(marks.length-1))]; seq.splice(seq.indexOf(m),0,f); total+=wd(f); k++;
  }
  const extra=(360-total)/seq.length;
  let a=-wd(seq[0])/2;
  for(const it of seq){
    const c=a+wd(it)/2; a+=wd(it)+extra;
    if(it.spacer) continue;
    const el=document.createElement('div');
    el.className='item ring';
    el.style.width=(it.w*u)+'px'; el.style.height=(it.h*u)+'px';
    el.innerHTML=it.draw.call(it,it.w,it.h);
    if(it.label) el.setAttribute('title',it.label);
    place(el,c,-6*u);
    ringspin.appendChild(el);
  }
  WALK={half:wd(CLINIC)/2, plaza:deg(130)+extra};

  // patients: five walk in bald, five walk out with hair
  ['bald','hair'].forEach(kind=>{for(let i=0;i<5;i++){
    const el=document.createElement('div'); el.className='item walker';
    el.style.width=(30*u)+'px'; el.style.height=(58*u)+'px';
    el.innerHTML=personSVG(kind,i+(kind==='hair'?2:0));
    ringspin.appendChild(el);
    walkers.push({el,kind,phase:i/5+(kind==='hair'?.1:0)});
  }});
  moveWalkers(performance.now()/1000);

  // headline + form ride on the globe face and stay put while the ring turns
  const hl=$('headline'); hl.style.fontSize=Math.round((narrow()?44:50)*u)+'px';
  place($('headItem'),0,-26*u,true);
  const form=$('login'); form.style.setProperty('--fw',Math.min(340,innerWidth*.8)+'px');
  place($('formItem'),0,-(26*u+hl.offsetHeight+16),true);
  $('greetText').style.fontSize=Math.round((narrow()?38:50)*u)+'px';
  place($('greetItem'),gapAngle(),-30*u,true);

  // clouds: a far ring that turns slower than the planet
  for(let i=0;i<34;i++){
    const ang=i*(360/34)+((i*37)%11), rad=R*(1.22+((i*53)%100)/100*.9), sz=(36+(i*17)%44)*u;
    const el=document.createElement('div'); el.className='item cloud';
    el.style.width=sz+'px'; el.style.height=sz/2+'px';
    el.innerHTML=cloudSVG;
    el.style.transform=`rotate(${ang}deg) translate(0px,${-rad}px) translate(-50%,-50%) rotate(${-ang+(i%5-2)*5}deg)`;
    const inner=el.firstChild; inner.style.animationDelay=(-i*0.7)+'s';
    clouddrift.appendChild(el);
  }
  drawWind();
  applyCamera(true);
}

function drawWind(){
  const w=innerWidth,h=innerHeight, s=$('wind');
  s.setAttribute('viewBox',`0 0 ${w} ${h}`);
  const lines=[[.62,.86,.78,.78],[.68,.93,.86,.85],[.55,.95,.66,.9],[.8,.7,.92,.64]];
  s.innerHTML=lines.map(([a,b,c,d])=>`<line x1="${a*w}" y1="${b*h}" x2="${c*w}" y2="${d*h}"/>`).join('');
}

/* ---------- login flow ---------- */
function setNav(i){[0,1,2].forEach(k=>{const n=$('n'+k); if(k===i) n.setAttribute('aria-current','step'); else n.removeAttribute('aria-current');});}
function nameFrom(email){
  const first=(email.split('@')[0]||'').split(/[._\-+0-9]/).filter(Boolean)[0]||'Misafir';
  return first.charAt(0).toLocaleUpperCase('tr')+first.slice(1).toLocaleLowerCase('tr');
}
function initials(email){
  const parts=(email.split('@')[0]||'').split(/[._\-+]/).filter(Boolean);
  return ((parts[0]||'N')[0]+((parts[1]||'')[0]||'')).toLocaleUpperCase('tr');
}
$('peek').addEventListener('click',e=>{
  const p=$('pass'), show=p.type==='password'; p.type=show?'text':'password';
  e.currentTarget.textContent=show?'Gizle':'Göster'; e.currentTarget.setAttribute('aria-pressed',String(show));
});
['email','pass'].forEach(id=>$(id).addEventListener('input',()=>{$(id).removeAttribute('aria-invalid');$('err').textContent='';}));

/* Giriş: sunucuda bin/panel.py → POST /api/giris {eposta, sifre} → 200 {ad, basHarf, rol} | 401.
   Dosya doğrudan açıldığında (file://) ya da adres ?demo ile açıldığında demo modu: her giriş kabul edilir. */
const DEMO = location.protocol==='file:' || new URLSearchParams(location.search).has('demo');
$('hint').hidden = !DEMO;
async function dogrula(email, sifre){
  if(DEMO) return {ok:true};
  try{
    const r=await fetch('/api/giris',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({eposta:email,sifre})});
    if(r.ok){ const j=await r.json().catch(()=>({})); return {ok:true, ad:j.ad, basHarf:j.basHarf, rol:j.rol}; }
    if(r.status===401) return {ok:false, hata:'E-posta ya da şifre hatalı.'};
    if(r.status===429) return {ok:false, hata:'Çok fazla deneme yapıldı. Birkaç dakika sonra tekrar dene.'};
    return {ok:false, hata:'Giriş şu an yapılamıyor. Biraz sonra tekrar dene.'};
  }catch(_){ return {ok:false, hata:'Sunucuya ulaşılamadı. Bağlantını kontrol edip tekrar dene.'}; }
}

$('login').addEventListener('submit',async e=>{
  e.preventDefault();
  if(phase!=='login' || $('go').disabled) return;
  const email=$('email').value.trim(), pass=$('pass').value;
  const okMail=/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
  if(!okMail){$('email').setAttribute('aria-invalid','true');$('err').textContent='E-posta adresini ad@sirket.com biçiminde yaz.';$('email').focus({preventScroll:true});return;}
  if(!pass){$('pass').setAttribute('aria-invalid','true');$('err').textContent='Şifreni yaz.';$('pass').focus({preventScroll:true});return;}
  const go=$('go'); go.disabled=true; go.textContent='Giriş yapılıyor…';
  const t0=performance.now(), sonuc=await dogrula(email, pass);
  if(!sonuc.ok){ go.disabled=false; go.textContent='Giriş yap'; $('err').textContent=sonuc.hata; $('pass').value=''; $('pass').focus({preventScroll:true}); return; }
  userName=sonuc.ad || nameFrom(email);
  $('gname').textContent=userName; $('uname').textContent=userName; $('avatar').textContent=sonuc.basHarf || initials(email);
  document.activeElement && document.activeElement.blur();
  setTimeout(toWelcome, Math.max(0,(reduce?50:450)-(performance.now()-t0)));
});

const timers=[];
function later(fn,ms){timers.push(setTimeout(fn,ms));}
function toWelcome(){
  phase='welcome'; setNav(1); applyCamera(false);
  later(()=>{$('formItem').classList.add('fade-away');$('headItem').classList.add('fade-away');}, reduce?0:500);
  const w=$('wind'); w.classList.remove('on'); void w.getBoundingClientRect(); w.classList.add('on');
  later(()=>$('greetInner').classList.add('on'), reduce?0:820);
  later(toOffice, reduce?1400:3300);
}
function toOffice(){
  phase='office'; setNav(2); applyCamera(false);
  later(()=>{mountOffice(); const a=$('app'); a.classList.add('on'); a.setAttribute('tabindex','-1'); a.focus({preventScroll:true}); tick();}, reduce?100:700);
}
$('logout').addEventListener('click',()=>{
  if(!DEMO) fetch('/api/cikis',{method:'POST',credentials:'same-origin'}).catch(()=>{});
  timers.splice(0).forEach(clearTimeout);
  $('app').classList.remove('on');
  $('greetInner').classList.remove('on');
  $('formItem').classList.remove('fade-away');$('headItem').classList.remove('fade-away');
  phase='login'; setNav(0);
  later(()=>applyCamera(false), reduce?0:350);
  const go=$('go'); go.disabled=false; go.textContent='Giriş yap'; $('pass').value='';
  later(()=>$('email').focus({preventScroll:true}),1300);
});

/* ---------- office app: port of the "Nove Kurul Ofisi 3D v4" component ---------- */
const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ORNEKLER = [
  "Q3 bütçe sapmasının ana nedenleri neler?",
  "ISO 9001 denetim bulguları kapandı mı?",
  "Çeyrek OKR'larında riskteki hedefler hangileri?",
  "Kurul sunumu için aylık özet hazırla",
  "Satış ekibinin açık teklifleri ne durumda?"
];
const BOLUMLER = {
  finans: { ad: "Finans Danışmanı", renk: "#2e9e74", kw: ["bütçe","nakit","gelir","kâr","kar ","maliyet","ebitda","finans","borç","yatırım","marj","sapma","ciro"],
    analiz: "Bütçe–gerçekleşen farkını kalem bazında ayırdı, kaynak tablolarıyla eşleştirdi.", sorgu: "Sapma tek seferlik mi, kalıcı mı? Ayrı göster.",
    revize: "Tek seferlik ve kalıcı etkiler ayrıldı; kalıcı kısım için öneri eklendi.", yanit: "Sapmanın kalıcı ve tek seferlik bileşenleri ayrıldı; kalıcı kısım için iki aksiyon önerisi var." },
  kalite: { ad: "Kalite Danışmanı", renk: "#4a6fb5", kw: ["kalite","iso","denetim","şikayet","hata","uygunsuzluk","süreç","standart","bulgu"],
    analiz: "Açık bulguları süreç ve kök nedene göre grupladı.", sorgu: "Tekrarlayan bulgular için kalıcı önlem var mı?",
    revize: "Tekrarlayan bulgulara düzeltici faaliyet planı eklendi.", yanit: "Açık bulgular süreç bazında gruplandı; tekrarlayanlar için düzeltici faaliyet planı hazır." },
  okr: { ad: "OKR Danışmanı", renk: "#c95564", kw: ["okr","hedef","anahtar sonuç","performans","çeyrek","öncelik"," kr"],
    analiz: "Her anahtar sonuç için hedef / şu an / kanıt tablosu çıkardı.", sorgu: "Riskteki KR'ların sahibi ve tarihi belli mi?",
    revize: "Riskteki KR'lara sahip ve kontrol tarihi atandı.", yanit: "Riskteki anahtar sonuçlar kanıtlarıyla listelendi; her birine sahip ve kontrol tarihi atandı." },
  rapor: { ad: "Raporlama Danışmanı", renk: "#c08a22", kw: ["rapor","sunum","özet","dashboard","tablo","grafik","aylık","bülten"],
    analiz: "İlgili danışman çıktılarını tek özet sayfasında derledi.", sorgu: "Kurul bu özetten hangi kararı verecek? Önce onu yaz.",
    revize: "Özet, karar gerektiren maddeyle başlayacak şekilde yeniden sıralandı.", yanit: "Özet hazır: önce karar gerektiren madde, ardından destekleyici bulgular." },
  satisMuduru: { ad: "Satış Müdürü", renk: "#d06a3a", kw: ["satış","müşteri","sipariş","teklif","pipeline","satıcı"],
    analiz: "Ekipten açık teklifleri ve kapanan satışları topladı, aşamalarına göre ayırdı.", sorgu: "Kapanma tahminleri hangi varsayıma dayanıyor?",
    revize: "Her teklife kapanma olasılığı ve dayanağı eklendi.", yanit: "Açık teklifler aşamalarına göre listelendi; her birinin kapanma olasılığı ve dayanağı belirtildi." }
};
const AJANLAR = {
  finans: { ad: "Finans Danışmanı", rol: "danışman", durum: "çalışıyor", renk: "#2e9e74", gorev: "Bütçe, nakit akışı, kârlılık ve yatırım sorularını analiz eder; rakamları kaynak tablolarına bağlar.", yetki: "Öneri verir · son karar CEO Ajanı'nda", kuyruk: "2 analiz sırada", cikti: "finans/eylul-nakit-analizi.md", btn: "Not bırak" },
  kalite: { ad: "Kalite Danışmanı", rol: "danışman", durum: "çalışıyor", renk: "#4a6fb5", gorev: "Süreç uygunsuzluklarını, denetim bulgularını ve müşteri şikayetlerini izler; kök neden ve düzeltici faaliyet önerir.", yetki: "Öneri verir · son karar CEO Ajanı'nda", kuyruk: "1 bulgu takipte", cikti: "kalite/tedarikci-uygunsuzluk.md", btn: "Not bırak" },
  okr: { ad: "OKR Danışmanı", rol: "danışman", durum: "çalışıyor", renk: "#c95564", gorev: "Şirket ve bölüm OKR'larının ilerlemesini kanıtla raporlar; riskteki anahtar sonuçları işaretler.", yetki: "Öneri verir · puanlama yapmaz", kuyruk: "çeyrek kapanışı hazırlığı", cikti: "okr/q4-taslak-inceleme.md", btn: "Not bırak" },
  rapor: { ad: "Raporlama Danışmanı", rol: "danışman", durum: "kurul paketi", renk: "#c08a22", gorev: "Kurul sunumlarını, aylık özetleri ve gösterge tablolarını derler; diğer danışmanların çıktısını tek dile çevirir.", yetki: "Derler · yorum CEO Ajanı'nda", kuyruk: "kurul paketi · 3 bölüm", cikti: "raporlama/ekim-kurul-paketi.md", btn: "Not bırak" },
  qa: { ad: "Q&A Danışmanı", rol: "giriş noktası", durum: "soru bekliyor", renk: "#8a5cc0", gorev: "Kurul üyelerinden gelen soruları karşılar, netleştirir ve onaylı yanıtı kurul masasına götürür.", yetki: "Kayıt açar · yanıt üretmez", kuyruk: "açık soru yok", cikti: "qa/soru-kayitlari.log", btn: "Not bırak" },
  dagitici: { ad: "İş Dağıtımcı", rol: "yönlendirici", durum: "hazır", renk: "#a77b3c", gorev: "Q&A'ya gelen soruyu okur, hangi danışmanın yanıtlayacağına karar verir ve soruyu o danışmanın masasına götürür.", yetki: "Yönlendirir · yanıt üretmez", kuyruk: "yönlendirme kuyruğu boş", cikti: "dagitim/yonlendirme.log", btn: "Kural ekle" },
  denetci: { ad: "Denetçi Ajan", rol: "kontrol", durum: "devriyede", renk: "#3b8fc4", gorev: "Masaların arasında dolaşır; her çıktıyı kaynak, hesap ve tutarlılık açısından kontrol eder.", yetki: "Geri çevirebilir · onaylayamaz", kuyruk: "denetim kuyruğu boş", cikti: "denetim/kontrol-kayitlari.log", btn: "Kural ekle" },
  ceo: { ad: "CEO Ajanı", rol: "son karar", durum: "odasında", renk: "#c9962f", gorev: "Son kararı verir. İşin doğru yapılıp yapılmadığını sorgular; gerekirse danışmandan revizyon ister.", yetki: "Onaylar / revizyon ister", kuyruk: "onay bekleyen yok", cikti: "karar/karar-defteri.md", btn: "Not bırak" },
  satisMuduru: { ad: "Satış Müdürü", rol: "yönetici", durum: "odasında", renk: "#d06a3a", gorev: "20 kişilik satış ekibini yönetir; teklif, müşteri ve sipariş sorularını yanıtlar, ekibin kapanan satışlarını takip eder.", yetki: "Ekibe görev verir · son karar CEO Ajanı'nda", kuyruk: "3 teklif onay bekliyor", cikti: "satis/haftalik-pipeline.md", btn: "Not bırak" },
  satis: { ad: "Satış Temsilcisi", rol: "satış ekibi", durum: "masasında", renk: "#d06a3a", gorev: "Müşteri görüşmelerini yürütür; her kapanan satışta odadaki zili çalar.", yetki: "Teklif hazırlar · onay Satış Müdürü'nde", kuyruk: "görüşme takvimi", cikti: "satis/gunluk-kapanis.log", btn: "Not bırak" },
  bos: { ad: "Boş oda", rol: "atanmamış", durum: "boş", renk: "#d9d4ca", gorev: "Yeni bir danışman bu odaya atanabilir — ör. Hukuk, İnsan Kaynakları, Strateji.", yetki: "—", kuyruk: "—", cikti: "—", btn: "+ Danışman ata" }
};
const ONAY = { karar: "Onaylandı", kararRenk: "#1f7a56", kararBg: "#e8f5ee" };
const SEED_DEFTER = [
  { tarih: "07.10.2026 16:42", soru: "Eylül nakit pozisyonu ile bütçe arasındaki farkın nedeni nedir?", bolum: "Finans", denetci: "Doğrulandı", ...ONAY },
  { tarih: "07.10.2026 11:05", soru: "Tedarikçi kaynaklı uygunsuzluklar hangi süreçte yoğunlaşıyor?", bolum: "Kalite", denetci: "1 varsayım işaretli", ...ONAY },
  { tarih: "06.10.2026 18:20", soru: "Q4 OKR taslağındaki hedefler stratejiyle uyumlu mu?", bolum: "OKR", denetci: "Doğrulandı", karar: "Revizyon istendi", kararRenk: "#8f6212", kararBg: "#fbf1dc" }
];
const BOS_ADIMLAR = [
  ["Q&A Danışmanı","soruyu alır","Kurul üyesinin sorusu tek giriş noktasından kayda girer.","#8a5cc0"],
  ["İş Dağıtımcı","bölümü seçer","Soruyu ilgili danışmanın masasına götürür.","#a77b3c"],
  ["Danışman","analiz eder","Finans, Kalite, OKR veya Raporlama.","#d9d4ca"],
  ["Denetçi Ajan","kontrol eder","Masaya gelir; kaynak, hesap ve tutarlılık.","#3b8fc4"],
  ["CEO Ajanı","sorgular","Danışman CEO odasına gider; CEO sorgular.","#c9962f"],
  ["Danışman","revize eder","CEO'nun sorusunu yanıtlar.","#d9d4ca"],
  ["CEO Ajanı","son kararı verir","Onay ya da revizyon.","#c9962f"],
  ["Q&A Danışmanı","kurula iletir","Yanıt kurul masasına götürülür.","#8a5cc0"]
];
const CEO_SORGULAR = true;
const st = { sec: "finans", panel: "akis", run: null, notlar: 0, defter: null };
let fbTimer = 0;

function zaman(d){ const p=n=>String(n).padStart(2,'0'); return `${p(d.getDate())}.${p(d.getMonth()+1)}.${d.getFullYear()} ${p(d.getHours())}:${p(d.getMinutes())}`; }
function tick(){ $('clock').textContent = zaman(new Date()); }
setInterval(tick, 30000); tick();

function yonlendir(metin){
  const t = " " + metin.toLocaleLowerCase("tr") + " ";
  let en = null, skor = 0, bulunan = [];
  Object.keys(BOLUMLER).forEach(k => { const hit = BOLUMLER[k].kw.filter(w => t.indexOf(w) !== -1); if (hit.length > skor) { skor = hit.length; en = k; bulunan = hit; } });
  if (!en) return { dept: "rapor", guven: 52, kw: [] };
  return { dept: en, guven: Math.min(96, 62 + skor * 12), kw: bulunan.map(w => w.trim()) };
}
function adimUret(r){
  const b = BOLUMLER[r.dept];
  const a = [
    { tip: "qa_al", kim: "Q&A Danışmanı", renk: "#8a5cc0", baslik: "soruyu aldı", metin: "Soru netleştirildi, kayıt açıldı." },
    { tip: "dagit", kim: "İş Dağıtımcı", renk: "#a77b3c", baslik: "bölümü seçti", metin: (r.kw.length ? "Eşleşen ifadeler: " + r.kw.join(", ") : "Net eşleşme yok — Raporlama'ya varsayılan") + " · güven %" + r.guven },
    { tip: "analiz", kim: b.ad, renk: b.renk, baslik: "analiz hazırlıyor", metin: b.analiz },
    { tip: "denetim", kim: "Denetçi Ajan", renk: "#3b8fc4", baslik: "kontrol etti", metin: "Kaynaklar ve hesaplar doğrulandı; 1 varsayım işaretlendi." }
  ];
  if (CEO_SORGULAR) {
    a.push({ tip: "ceo_sorgu", kim: "CEO Ajanı", renk: "#c9962f", baslik: "sorguladı", metin: "“" + b.sorgu + "”", balon: b.sorgu });
    a.push({ tip: "revize", kim: b.ad, renk: b.renk, baslik: "revize etti", metin: b.revize });
  }
  a.push({ tip: "ceo_onay", kim: "CEO Ajanı", renk: "#c9962f", baslik: "onayladı", metin: "Yanıt doğru ve eksiksiz; kurula sunulabilir." });
  a.push({ tip: "qa_ilet", kim: "Q&A Danışmanı", renk: "#8a5cc0", baslik: "kurula iletti", metin: "Yanıt kurul masasına götürüldü, Yanıt defterine işlendi." });
  return a;
}
function gonder(metin){
  const t = (typeof metin === "string" ? metin : $('question').value).trim();
  if (!t) { $('question').focus(); return; }
  if (st.run && !st.run.bitti) return;
  $('question').value = t;
  const r = yonlendir(t);
  st.run = { runId: Date.now(), soru: t, dept: r.dept, guven: r.guven, adimlar: adimUret(r), step: 0, bitti: false };
  st.panel = "akis"; renderApp(); adimGonder();
}
function adimGonder(){
  const r = st.run; if (!r || r.bitti) return;
  const a = r.adimlar[r.step];
  clearTimeout(fbTimer);
  window.dispatchEvent(new CustomEvent("nove-akis", { detail: { tip: a.tip, i: r.step, runId: r.runId, dept: r.dept, metin: a.balon } }));
  const id = r.runId, i = r.step;
  fbTimer = setTimeout(() => ilerle(id, i), window.__noveOfisHazir ? 25000 : 1800);
}
function ilerle(runId, i){
  const r = st.run;
  if (!r || r.runId !== runId || r.step !== i || r.bitti) return;
  const n = i + 1;
  if (n >= r.adimlar.length) {
    clearTimeout(fbTimer);
    const satir = { tarih: zaman(new Date()), soru: r.soru, bolum: BOLUMLER[r.dept].ad.split(" ")[0], denetci: "1 varsayım işaretli", ...ONAY };
    r.bitti = true; st.defter = [satir].concat(st.defter || SEED_DEFTER);
    $('question').value = '';
    renderApp(); return;
  }
  r.step = n; renderApp(); adimGonder();
}
window.addEventListener("nove-adim-bitti", e => { const d = e.detail || {}; ilerle(d.runId, d.i); });
window.addEventListener("nove-sec", e => { const k = e.detail && e.detail.key; if (k) { st.sec = k; st.panel = "ajan"; renderApp(); } });
window.__noveAyar = { hiz: 1 };

function renderApp(){
  const run = st.run, calisiyor = run && !run.bitti, akis = st.panel === "akis";
  const send = $('send'); send.textContent = calisiyor ? "Ofiste işleniyor…" : "Soruyu gönder"; send.setAttribute('aria-disabled', calisiyor ? 'true' : 'false');
  $('segAkis').setAttribute('aria-selected', String(akis)); $('segAjan').setAttribute('aria-selected', String(!akis));
  let h = '';
  if (akis) {
    const adimlar = run
      ? run.adimlar.map((a, i) => { const tamam = run.bitti || i < run.step, simdi = !run.bitti && i === run.step;
          return { kim: a.kim, baslik: a.baslik, metin: a.metin, renk: a.renk, op: tamam || simdi ? 1 : 0.4, isaret: tamam ? "✓" : String(i + 1),
            bg: tamam ? "#e8f5ee" : simdi ? "#1c1a17" : "#f4f2ee", fg: tamam ? "#1f7a56" : simdi ? "#ffffff" : "#9a9387", glow: simdi ? "0 0 0 4px rgba(201,150,47,.25)" : "none" }; })
      : BOS_ADIMLAR.map((b, i) => ({ kim: b[0], baslik: b[1], metin: b[2], renk: b[3], op: 0.8, isaret: String(i + 1), bg: "#f4f2ee", fg: "#9a9387", glow: "none" }));
    const yonVar = !!run && (run.bitti || run.step >= 1);
    h = `<div class="panel"><div><div class="lbl">SORU</div><div class="qtext">${esc(run ? run.soru : "Henüz soru yok. Yukarıdan bir soru yazın ya da örneklerden birini seçin.")}</div>`
      + (yonVar ? `<div class="yon">→ ${esc(BOLUMLER[run.dept].ad + " · güven %" + run.guven)}</div>` : '') + `</div><div>`
      + adimlar.map(a => `<div class="step" style="opacity:${a.op}"><div class="mark" style="background:${a.bg};color:${a.fg};box-shadow:${a.glow}">${a.isaret}</div><div style="min-width:0"><div class="kim"><i style="background:${a.renk}"></i><b>${esc(a.kim)}</b><span>${esc(a.baslik)}</span></div><div class="mt">${esc(a.metin)}</div></div></div>`).join('')
      + `</div>` + (run && run.bitti ? `<div class="answer"><div class="lbl">CEO ONAYLI YANIT</div><p>${esc(BOLUMLER[run.dept].yanit)}</p><small>${esc(BOLUMLER[run.dept].ad)} · Yanıt defterine işlendi</small></div>` : '') + `</div>`;
  } else {
    const k = st.sec, sel = AJANLAR[k] || (String(k).indexOf("satis") === 0 ? AJANLAR.satis : AJANLAR.finans);
    const masaMetin = k === "denetci" ? "Devriyeye gönder" : /^satis\d/.test(k) ? "Masasına gönder" : "Odasına gönder";
    h = `<div class="panel"><div class="card-head"><div class="figure" aria-hidden="true"><div class="h"></div><div class="b"></div><div class="s"></div><div class="t" style="background:${sel.renk}"></div></div><div style="min-width:0"><div class="card-name">${esc(sel.ad)}</div><div class="card-role">${esc(sel.rol)} · ${esc(sel.durum)}</div></div></div>`
      + `<div><div class="lbl">NE YAPAR</div><div class="body">${esc(sel.gorev)}</div></div>`
      + `<div><div class="lbl">YETKİ</div><div class="yetki">${esc(sel.yetki)}</div></div>`
      + `<div class="two"><div><div class="lbl">KUYRUK</div><div class="small">${esc(sel.kuyruk)}</div></div><div style="min-width:0"><div class="lbl">SON ÇIKTI</div><div class="cikti">${esc(sel.cikti)}</div></div></div>`
      + `<div class="acts">${k !== "bos" ? `<button type="button" class="btn-ghost" data-act="masa">${masaMetin}</button>` : ''}<button type="button" class="btn-dark" data-act="not">${esc(sel.btn)}</button></div>`
      + `<div class="note">${st.notlar === 0 ? "bu oturumda not bırakılmadı" : st.notlar + " not bu oturumda bırakıldı"}</div></div>`;
  }
  $('panel').innerHTML = h;
  const defter = st.defter || SEED_DEFTER;
  $('defterAdet').textContent = defter.length + ' kayıt';
  $('defterRows').innerHTML = defter.map(d => `<div class="tr"><div class="d">${esc(d.tarih)}</div><div class="q">${esc(d.soru)}</div><div class="c">${esc(d.bolum)}</div><div class="c">${esc(d.denetci)}</div><div><span class="badge" style="background:${d.kararBg};color:${d.kararRenk}">${esc(d.karar)}</span></div></div>`).join('');
}
$('chips').insertAdjacentHTML('beforeend', ORNEKLER.map(m => `<button type="button" class="chip">${esc(m)}</button>`).join(''));
$('chips').addEventListener('click', e => { const b = e.target.closest('.chip'); if (b) gonder(b.textContent); });
$('ask').addEventListener('submit', e => { e.preventDefault(); gonder(); });
$('segAkis').addEventListener('click', () => { st.panel = "akis"; renderApp(); });
$('segAjan').addEventListener('click', () => { st.panel = "ajan"; renderApp(); });
$('panel').addEventListener('click', e => {
  const b = e.target.closest('[data-act]'); if (!b) return;
  if (b.dataset.act === 'masa') window.dispatchEvent(new CustomEvent("nove-komut", { detail: { key: st.sec, cmd: "masa" } }));
  else { st.notlar++; renderApp(); }
});
// in-app anchor links scroll inside the app layer, never the page
document.querySelectorAll('.tabs a').forEach(a => a.addEventListener('click', e => {
  e.preventDefault();
  document.querySelectorAll('.tabs a').forEach(x => x.classList.toggle('on', x === a));
  const t = a.getAttribute('href') === '#defter' ? $('defter') : null;
  $('app').scrollTo({ top: t ? t.offsetTop - 70 : 0, behavior: reduce ? 'auto' : 'smooth' });
}));
renderApp();

function mountOffice(){
  if ($('stagebox').querySelector('nove-ofis-4')) return;
  $('stagebox').insertBefore(document.createElement('nove-ofis-4'), $('stagebox').firstChild);
}

/* gentle mouse parallax on the cloud layer only */
addEventListener('pointermove',e=>{
  if(reduce||phase==='office') return;
  const dx=(e.clientX/innerWidth-.5), dy=(e.clientY/innerHeight-.5);
  cloudspin.style.translate=`${dx*-14}px ${dy*-8}px`;
});

function moveWalkers(t){
  const speed=26/520*57.2958;                       // 26 design px per second, in degrees
  const dist=WALK.half+WALK.plaza*.85, cycle=dist/speed;
  for(const w of walkers){
    const f=((t/cycle)+w.phase)%1;
    let ang, op;
    if(w.kind==='bald'){ ang=dist*(1-f); op=Math.min(1,f/.08,(1-f)/.07); }   // from the right, into the door
    else { ang=-dist*f; op=Math.min(1,f/.07,(1-f)/.08); }                     // out of the door, off to the left
    place(w.el,ang,-3*u); w.el.style.opacity=op.toFixed(2);
  }
}
let lastT=performance.now();
function turn(now){
  const dt=Math.min(.05,(now-lastT)/1000); lastT=now;
  if(!(phase==='office' && $('app').classList.contains('on'))){
    if(!reduce) drift-=dt*DRIFT;
    ringspin.style.transform=`rotate(${drift}deg)`;
    clouddrift.style.transform=`rotate(${drift*.5}deg)`;
    if(!reduce) moveWalkers(now/1000);
  }
  requestAnimationFrame(turn);
}
requestAnimationFrame(turn);

let rt, lastW=0, lastH=0;
function relayout(){ if(innerWidth<50||innerHeight<50) return; if(innerWidth===lastW&&innerHeight===lastH) return; lastW=innerWidth; lastH=innerHeight; layout(); }
addEventListener('resize',()=>{clearTimeout(rt); rt=setTimeout(relayout,120);});
if('ResizeObserver' in window) new ResizeObserver(()=>{clearTimeout(rt); rt=setTimeout(relayout,60);}).observe(document.documentElement);
(function boot(){ if(innerWidth<50||innerHeight<50) return requestAnimationFrame(boot); relayout();
  // #ofis deep link (yalnız demo): girişi atlayıp ofisi açar
  if(DEMO && location.hash==='#ofis'){ phase='office'; setNav(2); applyCamera(true); mountOffice(); $('app').classList.add('on'); }
})();
// focusing a field inside the rotated planet must never scroll the stage
const stage=$('stage'); stage.addEventListener('scroll',()=>{stage.scrollTop=0; stage.scrollLeft=0;});
addEventListener('scroll',()=>{ if(scrollX||scrollY) scrollTo(0,0); });
})();
