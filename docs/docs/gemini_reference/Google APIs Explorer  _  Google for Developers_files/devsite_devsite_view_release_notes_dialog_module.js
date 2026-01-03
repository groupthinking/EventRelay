(function(_ds){var window=this;var GSa=function(a){a.eventHandler.listen(a,"DropdownItemClicked",b=>{FSa(a,b)})},FSa=async function(a,b){const c=b.getBrowserEvent().detail.id;b=a.querySelector(".devsite-dialog-contents");const d=a.querySelector(`#date-section-${c}`);let e,f,g,h;const k=((g=d==null?void 0:(e=d.getBoundingClientRect())==null?void 0:e.top)!=null?g:0)-((h=b==null?void 0:(f=b.getBoundingClientRect())==null?void 0:f.top)!=null?h:0);d&&b&&b.scrollBy({top:k,behavior:"smooth"});let l,m;a.gp=(m=(l=a.xq.find(n=>n.id===c))==
null?void 0:l.title)!=null?m:"";a.o.fb(a.gp)},ISa=function(a){const b=new IntersectionObserver(c=>{c.forEach(d=>{HSa(a,d.isIntersecting,d)})},{root:a.querySelector(".devsite-dialog-contents")});a.querySelectorAll(".release-note-date-section .release-note").forEach(c=>{b.observe(c)})},HSa=function(a,b,c){let d;const e={id:(d=c.target.getAttribute("id"))!=null?d:"",type:Number(c.target.getAttribute("type"))};if(b){let f;a.Sl=[...((f=a.Sl)!=null?f:[]),e]}else a.Sl=[...a.Sl.filter(f=>f.id!==e.id)]},JSa=
function(a){switch(a){case 4:return{title:"Feature",color:"green"};case 8:return{title:"Announcement",color:"yellow"};case 2:return{title:"Change",color:"yellow"};case 9:return{title:"Libraries",color:"blue"};case 3:return{title:"Fixed",color:"blue"};case 1:return{title:"Breaking",color:"red"};case 5:return{title:"Deprecated",color:"red"};case 6:return{title:"Issue",color:"red"};case 7:return{title:"Security",color:"orange"};default:return{title:"Unspecified",color:"grey"}}},I2=function(a,b){b=JSa(b);
return(0,_ds.N)` <span
      class="release-note-type-chip
          ${a} ${b.color}">
      ${b.title}
    </span>`},KSa=function(a,b){const c=b.replace(/,?\s/g,"").toLowerCase();let d;return(0,_ds.N)`
      <div class="release-note-date-section" id="date-section-${c}">
        <h3 class="release-note-date-header">${b}</h3>
        ${[...((d=a.releaseNotes.get(b))!=null?d:[])].map((e,f)=>{f=`${c}-${f}`;var g;(g=_ds.ti(e,_ds.tna,4))?(g=_ds.Ii(g,2),g=g===null||g===void 0?null:_ds.Cf(g)):g=null;return(0,_ds.N)` <div
        class="release-note"
        id="${f}"
        type="${_ds.B(e,2)}">
        ${I2("large",_ds.B(e,2))}
        <div class="release-note-content">
          ${g?(0,_ds.N)`${(0,_ds.KG)(g)}`:(0,_ds.N)`<p>${_ds.A(e,1)}</p>`}
        </div>
      </div>`})}
      </div>
    `},J2=class extends _ds.Pv{constructor(){super(["devsite-dialog","devsite-dropdown-list"]);this.eventHandler=new _ds.v;this.releaseNotes=new Map;this.hideFooter=!1;this.gp="";this.xq=[];this.Sl=[];this.o=new _ds.Zg(async a=>{this.Da({category:"Site-Wide Custom Events",action:"release notes: view old note",label:`${await _ds.as(_ds.E().href)} : ${a}`})},100)}Wa(){return this}async connectedCallback(){super.connectedCallback();this.gp=[...this.releaseNotes.keys()][0];this.xq=[...this.releaseNotes.keys()].map(a=>
({id:a.replace(/,?\s/g,"").toLowerCase(),title:a}));GSa(this)}disconnectedCallback(){super.disconnectedCallback()}j(a){super.j(a);ISa(this)}render(){return(0,_ds.N)`
      <div class="devsite-dialog-header">
        <div>
          <h3 class="no-link title">
            ${"Release Notes"}
          </h3>
          <div class="chip-wrapper">
            ${[...(new Set(this.Sl.map(a=>a.type)))].map(a=>I2("small",a))}
          </div>
        </div>
        <devsite-dropdown-list
            .listItems=${this.xq}>
          <p slot="toggle" class="selected-date-toggle">${this.gp}</p>
        </devsite-dropdown-list>
      </div>
      <div class="devsite-dialog-contents">
        ${[...this.releaseNotes.keys()].map(a=>KSa(this,a))}
      </div>
      ${_ds.L(this.hideFooter,()=>"",()=>(0,_ds.N)`
              <div class="devsite-dialog-footer devsite-dialog-buttons">
                <button class="button devsite-dialog-close">
                  Close
                </button>
              </div>
            `)}
      `}};_ds.y([_ds.G({type:Map}),_ds.z("design:type",Object)],J2.prototype,"releaseNotes",void 0);_ds.y([_ds.G({type:Boolean}),_ds.z("design:type",Object)],J2.prototype,"hideFooter",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],J2.prototype,"gp",void 0);_ds.y([_ds.I(),_ds.z("design:type",Array)],J2.prototype,"xq",void 0);_ds.y([_ds.I(),_ds.z("design:type",Array)],J2.prototype,"Sl",void 0);try{customElements.define("devsite-view-release-notes-dialog",J2)}catch(a){console.warn("devsite.app.customElement.DevsiteViewReleaseNotesDialog",a)};})(_ds_www);
