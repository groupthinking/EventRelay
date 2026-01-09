(function(_ds){var window=this;var vEa=async function(a,b){const c=a.o;let d;const e=b.id!==((d=a.qa)==null?void 0:d.id);e&&(a.className=b.id,a.eventLabel=`devsite-callout-${b.id}`,a.o=new _ds.zH(b.origin,a.eventLabel));a.qa=b;c&&e&&await _ds.yH(c)},wEa=async function(a){a.eventHandler.listen(document.body,"devsite-before-page-change",()=>{a.hide()})},xEa=async function(a,b){let c;((c=a.callout)==null?0:c.aj)&&a.callout.aj(b);await a.hide();a.Da({category:"Site-Wide Custom Events",action:"callout-dismiss",label:a.eventLabel})},
bT=async function(a,b){let c;((c=a.callout)==null?0:c.Ci)&&a.callout.Ci(b);let d;((d=a.callout)==null?0:d.Co)||await a.hide();a.Da({category:"Site-Wide Custom Events",action:"callout-action",label:a.eventLabel})},yEa=function(a){let b,c;if(((b=a.callout)==null?0:b.ph)&&`${(c=a.callout)==null?void 0:c.ph}`){let d,e;return(0,_ds.N)`<div class="devsite-callout-branding">
          <img
            class="devsite-callout-branding-image"
            src="${(d=a.callout)==null?void 0:d.ph}"
            alt="${((e=a.callout)==null?void 0:e.zk)||""}" />
        </div>
        <hr />`}return(0,_ds.N)``},zEa=function(a){let b,c;if(((b=a.callout)==null?0:b.Sw)&&`${(c=a.callout)==null?void 0:c.Sw}`){let d,e;return(0,_ds.N)`<div class="devsite-callout-hero">
        <img
          class="devsite-callout-hero-image"
          src="${(d=a.callout)==null?void 0:d.Sw}"
          alt="${((e=a.callout)==null?void 0:e.XJ)||""}" />
      </div>`}return(0,_ds.N)``},AEa=function(a){let b;if((b=a.callout)==null?0:b.lB)return(0,_ds.N)``;let c;return(0,_ds.N)` <div class="devsite-callout-header">
        <h2>${((c=a.callout)==null?void 0:c.title)||""}</h2>
      </div>`},BEa=function(a){let b;if((b=a.callout)==null?0:b.loading)return(0,_ds.N)`<div class="devsite-callout-body"
        ><devsite-spinner size="24"></devsite-spinner
      ></div>`;let c,d;var e;if(((c=a.callout)==null?0:c.body)&&`${(d=a.callout)==null?void 0:d.body}`){{let f;if(((f=a.callout)==null?void 0:f.body)instanceof _ds.Bf){let g;a=(0,_ds.N)`${(0,_ds.KG)((g=a.callout)==null?void 0:g.body)}`}else a=(0,_ds.N)`${(e=a.callout)==null?void 0:e.body}`}e=(0,_ds.N)`<div class="devsite-callout-body">
        ${a}
      </div>`}else e=(0,_ds.N)``;return e},CEa=function(a){var b;if((b=a.callout)==null||!b.ef)return(0,_ds.N)``;var c;b=(0,_ds.Pt)({button:!0,"button-primary":!0,"devsite-callout-action":!0,"button-disabled":((c=a.callout)==null?void 0:c.Zz)||!1});let d;c=(d=a.callout)==null?void 0:d.XG;let e;if((e=a.callout)==null?0:e.Xp){let g,h;return(0,_ds.N)`<a
        @click=${k=>{bT(a,k)}}
        href="${((g=a.callout)==null?void 0:g.Xp)||""}"
        class="${b}"
        aria-label=${c!=null?c:_ds.Pu}
        data-title=${c!=null?c:_ds.Pu}>
        ${((h=a.callout)==null?void 0:h.ef)||""}
      </a>`}let f;return(0,_ds.N)`<button
        @click=${g=>{bT(a,g)}}
        class="${b}"
        aria-label=${c!=null?c:_ds.Pu}
        data-title=${c!=null?c:_ds.Pu}>
        ${((f=a.callout)==null?void 0:f.ef)||""}
      </button>`},cT=class extends _ds.Pv{set callout(a){vEa(this,a)}get callout(){return this.qa}get open(){let a;return((a=this.oa.value)==null?void 0:a.open)||!1}constructor(){super(["devsite-spinner"]);this.eventHandler=new _ds.v;this.eventLabel="";this.qa=this.ea=this.o=null;this.oa=new _ds.GG}connectedCallback(){super.connectedCallback();wEa(this)}disconnectedCallback(){super.disconnectedCallback();let a;(a=this.o)==null||a.cancel()}Wa(){return this}async ready(){await this.m}async show(){await this.ready();
if(!this.open){var a;await ((a=this.o)==null?void 0:a.schedule(()=>{document.activeElement instanceof HTMLElement&&(this.ea=document.activeElement);var b;(b=this.oa.value)==null||b.show();let c;(c=this.querySelector(".devsite-callout-action"))==null||c.focus();let d;b={message:(((d=this.callout)==null?void 0:d.title)||"")+" dialog opened"};document.body.dispatchEvent(new CustomEvent("devsite-a11y-announce",{detail:b}));this.Da({category:"Site-Wide Custom Events",action:"callout-impression",label:this.eventLabel,
nonInteraction:!0})},()=>{let b;(b=this.oa.value)==null||b.close();let c;(c=this.querySelector(".devsite-callout-action"))==null||c.blur();this.ea&&this.ea.focus()}))}}async hide(){await this.ready();let a;await ((a=this.o)==null?void 0:_ds.yH(a))}render(){if(!this.callout)return(0,_ds.N)``;let a;return(0,_ds.N)`
      <dialog
        closedby="none"
        ${(0,_ds.IG)(this.oa)}
        aria-label="${((a=this.callout)==null?void 0:a.title)||""}"
        class="devsite-callout">
        ${yEa(this)} ${zEa(this)}
        ${AEa(this)} ${BEa(this)}
        <div class="devsite-callout-buttons">
          <button
            @click=${b=>{xEa(this,b)}}
            class="button button-dismiss devsite-callout-dismiss">
            ${"Dismiss"}
          </button>
          ${CEa(this)}
        </div>
      </dialog>
    `}};_ds.y([_ds.G({Ha:!1}),_ds.z("design:type",Object),_ds.z("design:paramtypes",[Object])],cT.prototype,"callout",null);try{customElements.define("devsite-callout",cT)}catch(a){console.warn("Unrecognized DevSite custom element - DevsiteCallout",a)};})(_ds_www);
