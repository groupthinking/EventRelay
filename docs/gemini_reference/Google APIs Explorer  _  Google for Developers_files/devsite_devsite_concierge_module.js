(function(_ds){var window=this;var OT=function(){return"devsite-concierge"},qFa=function(a){a.eventHandler.listen(a,"devsite-concierge-close-panel",()=>{document.body.getAttribute("concierge")==="modal"&&(a.dispatchEvent(new CustomEvent("devsite-sitemask-hide",{bubbles:!0})),a.Mg=!1);_ds.Ov(a,{type:"sidePanel",name:"closed",metadata:{id:a.Ud,name:a.tagName.toLowerCase(),action:"close button click"}});PT(a,!0)});a.eventHandler.listen(a,"devsite-concierge-open-panel",c=>{c=c.getBrowserEvent().detail.hC;a.o(c,!0)});a.eventHandler.listen(document.body,
"devsite-sitemask-hidden",()=>{document.body.getAttribute("concierge")==="modal"&&(a.Mg=!1,_ds.Nv(a,"concierge","open",document.body))});a.eventHandler.listen(a,"devsite-concierge-fullscreen-panel",()=>{a.Mg=!0;_ds.Nv(a,"concierge","modal",document.body);a.dispatchEvent(new CustomEvent("devsite-sitemask-show",{bubbles:!0}));_ds.Ov(a,{type:"sidePanel",name:"fullscreen",metadata:{id:a.Ud,name:a.tagName.toLowerCase()}})});a.eventHandler.listen(a,"devsite-concierge-dock-panel",c=>{c=c.getBrowserEvent();
a.Mg=!1;_ds.Nv(a,"concierge","open",document.body);c&&c.detail&&c.detail.hideSitemask&&a.dispatchEvent(new CustomEvent("devsite-sitemask-hide",{bubbles:!0}))});a.eventHandler.listen(a,"devsite-concierge-set-notification",c=>{c=c.getBrowserEvent();pFa(a,c)});a.eventHandler.listen(a,"devsite-concierge-clear-notification",c=>{switch(c.getBrowserEvent().detail.tagName){case "devsite-concierge-ai-panel":a.pk=!1;a.Lm="";break;case "devsite-concierge-info-panel":a.ql=!1;a.Xn="";break;case "devsite-concierge-recommendations-panel":a.Ml=
!1;a.Xo="";break;case "devsite-concierge-api-explorer-panel":a.qk=!1;a.Om="";break;case "devsite-concierge-my-activity-panel":a.Fl=!1,a.Mo=""}});a.eventHandler.listen(document.body,"devsite-before-page-change",()=>{a.largeViewport||PT(a)});const b=window.matchMedia("(min-width: 1400px)");a.largeViewport=b.matches;a.eventHandler.listen(b,"change",c=>{c=c.getBrowserEvent().matches;a.largeViewport=c});a.eventHandler.listen(document.body,"devsite-page-changed",()=>{QT(a)});a.eventHandler.listen(document.body,
"devsite-viewport-change",c=>{c=c.getBrowserEvent().detail.viewport==="viewport--desktop";if(a.Mk)a.Xw=c,_ds.mv(a);else if(!c){c=document.body.getAttribute("concierge")==="modal";const d=document.body.getAttribute("concierge")==="open";c&&(a.dispatchEvent(new CustomEvent("devsite-sitemask-hide",{bubbles:!0})),a.Mg=!1);d&&(a.panelOpen=!1);if(c||d)PT(a,!0),_ds.mv(a)}});if(a.Mk){let c;(c=window.document.getElementsByClassName("devsite-devguide-mobile-button").item(0))==null||c.addEventListener("click",
()=>{a.o("devsite-concierge-info-panel",!1)})}},QT=function(a){const b=_ds.E(),c=document.body.getAttribute("type");let d=document.body.hasAttribute("display-toc");if(c==="lcat"||c==="codelab")d=!1;else if(a.tenantId===1){if(b.pathname.match("^/learn[/]?")||b.pathname.match("^/community[/]?")||b.pathname.match("^/solutions[/]?"))d=!0;c==="profile"&&(d=!0)}d?_ds.Nv(a,"concierge",a.Mg?"modal":a.panelOpen?"open":"closed",document.body):_ds.Nv(a,"concierge","hide",document.body);return d},PT=async function(a,
b=!1){b&&await (await _ds.w()).getStorage().set("devguide_state","","CLOSED");await RT(a,!1)},pFa=async function(a,b){const c=b.detail.tagName;b=b.detail.message;if(a.Ud!==c)switch(c){case "devsite-concierge-ai-panel":a.pk&&(a.pk=!1,a.Lm="",_ds.mv(a),await a.m);a.pk=!0;b&&(a.Lm=b);break;case "devsite-concierge-info-panel":a.ql&&(a.ql=!1,a.Xn="",_ds.mv(a),await a.m);a.ql=!0;b&&(a.Xn=b);break;case "devsite-concierge-recommendations-panel":a.Ml&&(a.Ml=!1,a.Xo="",_ds.mv(a),await a.m);a.Ml=!0;b&&(a.Xo=
b);break;case "devsite-concierge-api-explorer-panel":a.qk&&(a.qk=!1,a.Om="",_ds.mv(a),await a.m);a.qk=!0;b&&(a.Om=b);break;case "devsite-concierge-my-activity-panel":a.Fl&&(a.Fl=!1,a.Mo="",_ds.mv(a),await a.m),a.Fl=!0,b&&(a.Mo=b)}},ST=function(a,b,c=0){if(b!==document.body&&b.parentElement){var {x:d,y:e,height:f}=b.getBoundingClientRect();return e+f>c&&d>0&&d<window.innerWidth?b:ST(a,b.parentElement,c)}},rFa=async function(a,b){await _ds.w();var c,d,e;const f=((c=document)==null?void 0:(d=c.documentElement)==
null?void 0:(e=d.getAttribute("dir"))==null?void 0:e.toLowerCase())==="rtl";(c=document.querySelector("devsite-header"))&&await customElements.whenDefined("devsite-header");c=(c==null?void 0:c.qa())||0;if(a=ST(a,b,c)){var {x:g,y:h,width:k,height:l}=a.getBoundingClientRect();b=f?g+k:g;c=Math.max(h,c);d=f?Math.max(0,g):Math.min(g+k,window.innerWidth);e=Math.min(l-Math.abs(h),window.innerHeight);var m=Math.round(Math.max(5,(d-b)*.01));m=f?-m:m;var n=Math.round(Math.max(5,(e-c)*.01));g=b;h=c;for(var p=
document.elementFromPoint(g,h),q=!1;p===a||!a.contains(p)||!q;){p&&(q=p.getBoundingClientRect().top>=c);g+=m;f?g<d&&(g=b,h+=n):g>d&&(g=b,h+=n);if(h>e)return;p=document.elementFromPoint(g,h)}return p}},RT=async function(a,b,c=""){a.Ud=c;if(a.panelOpen!==b)if(c=document.querySelector(".devsite-article-body")){var d=await rFa(a,c);d?(await _ds.Qg(),c=d.getBoundingClientRect().top||0,a.panelOpen=b,document.body.dispatchEvent(new CustomEvent("devsite-sticky-resize",{bubbles:!0})),await _ds.Ql(),a=d.getBoundingClientRect().top||
0,a-c!==0&&window.scrollBy({left:window.scrollX,top:a-c}),_ds.Rg()):a.panelOpen=b}else a.panelOpen=b},TT=function(a,b){a.panelOpen||_ds.Ov(a,{type:"sidePanel",name:"opened",metadata:{id:b,name:a.tagName.toLowerCase(),action:"menu item click"}});a.Ud!==b?(a.Da({category:"Developer Concierge",action:a.panelOpen?"Switch Tab":"Open Panel",label:b}),_ds.Ov(a,{type:"sidePanel",name:"tabClick",metadata:{id:b,name:a.tagName.toLowerCase()}}),a.o(b,!0)):a.Mg||(_ds.Ov(a,{type:"sidePanel",name:"closed",metadata:{id:b,
name:a.tagName.toLowerCase(),action:"menu item click"}}),PT(a,!0))},sFa=function(a,b,c,d){return c?d?(0,_ds.N)`<div class="devsite-concierge-notification-dot"></div>
      <div
        class="devsite-concierge-notification"
        @click="${()=>{TT(a,b)}}"
        >${d}</div
      >`:(0,_ds.N)`<div class="devsite-concierge-notification-dot"></div>`:(0,_ds.N)``},UT=function(a,b,c=!1){if(!c)return(0,_ds.N)``;a.oa.push(b);switch(b){case "devsite-concierge-ai-panel":return(0,_ds.N)` <devsite-concierge-ai-panel
          ?active="${a.Ud===b}">
        </devsite-concierge-ai-panel>`;case "devsite-concierge-info-panel":return(0,_ds.N)` <devsite-concierge-info-panel
          ?active="${a.Ud===b}">
        </devsite-concierge-info-panel>`;case "devsite-concierge-recommendations-panel":return(0,_ds.N)` <devsite-concierge-recommendations-panel
          ?active="${a.Ud===b}">
        </devsite-concierge-recommendations-panel>`;case "devsite-concierge-api-explorer-panel":return(0,_ds.N)` <devsite-concierge-api-explorer-panel
          ?active="${a.Ud===b}">
        </devsite-concierge-api-explorer-panel>`;case "devsite-concierge-my-activity-panel":return(0,_ds.N)` <devsite-concierge-my-activity-panel
          ?active="${a.Ud===b}">
        </devsite-concierge-my-activity-panel>`;default:return(0,_ds.N)` <div ?active="${a.Ud===b}">
          ${b} element missing
        </div>`}},VT=function(a,b,c,d,e,f=!1,g=!1,h=""){return f?(0,_ds.N)`
      <button class="${(0,_ds.Pt)({"devsite-concierge-menu-item--selected":a.Ud===b,"devsite-concierge-menu-item":!0,[`${b}--menu-item`]:!0})}"
          @click="${()=>{TT(a,b)}}"
          data-title="${d}">
        <div class="devsite-concierge-menu-icon" aria-hidden="true">
          ${e}
        </div>
        <div class="devsite-concierge-menu-title">
          ${c}
        </div>
        ${sFa(a,b,g,h)}
      </button>`:(0,_ds.N)``},tFa=function(a){return(0,_ds.N)` <div
      aria-label="${"Side panel menu"}"
      aria-orientation="${a.Mk&&!a.Mg&&a.panelOpen&&a.Xw?"horizontal":"vertical"}"
      class="devsite-concierge-menu"
      role="toolbar"
      @keydown="${b=>{if(b.key==="ArrowUp"||b.key==="ArrowDown"||b.key==="ArrowLeft"||b.key==="ArrowRight"){b.preventDefault();let c=0;const d=document.activeElement,e=a.querySelectorAll(".devsite-concierge-menu-item");d&&(c=[...e].indexOf(d));c=b.key==="ArrowUp"||b.key==="ArrowLeft"?c===0?e.length-1:c-1:c===e.length-1?0:c+1;e[c].focus()}}}">
      ${VT(a,"devsite-concierge-info-panel","Info","Page info",_ds.fxa,a.ft,a.ql,a.Xn)}
      ${VT(a,"devsite-concierge-ai-panel","Chat","Ask about this page",_ds.Gwa,a.Zs,a.pk,a.Lm)}
      ${VT(a,"devsite-concierge-recommendations-panel","Related","Related Pages",_ds.lxa,a.qt,a.Ml,a.Xo)}
      ${VT(a,"devsite-concierge-api-explorer-panel","API","APIs Explorer",_ds.Rwa,a.bt,a.qk,a.Om)}
      ${VT(a,"devsite-concierge-my-activity-panel","Recent","Recent Activity",(0,_ds.N)`<svg
    width="20"
    height="18"
    viewBox="0 0 20 18"
    fill="none"
    xmlns="http://www.w3.org/2000/svg">
    <path
      d="M17 12C15.7 12 14.6 12.84 14.18 14H9C7.9 14 7 13.1 7 12C7 10.9 7.9 10 9 10H11C13.21 10 15 8.21 15 6C15 3.79 13.21 2 11 2H5.82C5.4 0.84 4.3 0 3 0C1.34 0 0 1.34 0 3C0 4.66 1.34 6 3 6C4.3 6 5.4 5.16 5.82 4H11C12.1 4 13 4.9 13 6C13 7.1 12.1 8 11 8H9C6.79 8 5 9.79 5 12C5 14.21 6.79 16 9 16H14.18C14.59 17.16 15.69 18 17 18C18.66 18 20 16.66 20 15C20 13.34 18.66 12 17 12ZM3 4C2.45 4 2 3.55 2 3C2 2.45 2.45 2 3 2C3.55 2 4 2.45 4 3C4 3.55 3.55 4 3 4Z"
      fill="#1967D2" />
  </svg>`,a.jt,a.Fl,a.Mo)}
    </div>`},WT=class extends _ds.Pv{Wa(){return this}constructor(){super(["devsite-tooltip"]);this.Mg=this.qt=this.jt=this.ft=this.bt=this.Zs=!1;this.Xw=_ds.eh()==="viewport--desktop";this.Ml=this.Fl=this.ql=this.qk=this.pk=this.Mk=!1;this.Ud=this.Xo=this.Mo=this.Xn=this.Om=this.Lm="";this.panelOpen=this.largeViewport=!1;this.eventHandler=new _ds.v;this.oa=[];this.ea="UNDEFINED";this.tenantId=0;_ds.Mv(this,(0,_ds.Tf)`concierge`)}async connectedCallback(){var a=await _ds.w();this.tenantId=a.getTenantId()||
0;this.Mk=await a.hasMendelFlagAccess("Concierge","enable_devguide_mobile_view");super.connectedCallback();qFa(this);if(QT(this)&&(a=_ds.E(),a.searchParams.has("devguide")))switch(a.searchParams.get("devguide")){case "ai":await this.o("devsite-concierge-ai-panel",!1);break;case "recommendations":await this.o("devsite-concierge-recommendations-panel",!1);break;case "api_explorer":await this.o("devsite-concierge-api-explorer-panel",!1);break;case "my_activity":await this.o("devsite-concierge-my-activity-panel",
!1);break;default:await this.o("devsite-concierge-info-panel",!1)}}disconnectedCallback(){super.disconnectedCallback();this.eventHandler.removeAll();document.body.removeAttribute("concierge")}async qa(a,b){await this.o("devsite-concierge-ai-panel");const c=this.querySelector("devsite-concierge-ai-panel"),d=_ds.E();d.search="";c&&await _ds.uN(c,{code:a,language:b,url:d.href})}async o(a,b=!1){b&&await (await _ds.w()).getStorage().set("devguide_state","","OPEN");await RT(this,!0,a)}static get observedAttributes(){return["data-ai-panel",
"data-api-explorer-panel","data-info-panel","data-my-activity-panel","data-recommendations-panel"]}attributeChangedCallback(a){switch(a){case "data-ai-panel":this.Zs=this.hasAttribute("data-ai-panel");_ds.Lv("devsite-concierge-ai-panel");break;case "data-info-panel":this.ft=this.hasAttribute("data-info-panel");_ds.Lv("devsite-concierge-info-panel");break;case "data-recommendations-panel":this.qt=this.hasAttribute("data-recommendations-panel");_ds.Lv("devsite-concierge-recommendations-panel");break;
case "data-api-explorer-panel":this.bt=this.hasAttribute("data-api-explorer-panel");_ds.Lv("devsite-concierge-api-explorer-panel");break;case "data-my-activity-panel":this.jt=this.hasAttribute("data-my-activity-panel"),_ds.Lv("devsite-concierge-my-activity-panel")}}async j(a){super.j(a);this.oa.length>0&&_ds.Ov(this,{type:"sidePanel",name:"impression",metadata:{id:this.oa[0],name:this.tagName.toLowerCase()}});a.has("largeViewport")&&this.Ud===""&&this.largeViewport&&(this.ea=await (await _ds.w()).getStorage().get("devguide_state",
"")||"UNDEFINED",this.ea!=="CLOSED"&&(await this.o(this.oa[0]),this.Da({category:"Developer Concierge",action:"Opened by default"})))}updated(a){super.updated(a);a.has("panelOpen")&&QT(this)}ra(){return QT(this)}render(){return(0,_ds.N)` <div class="${(0,_ds.Pt)({"devsite-concierge-panel-open":this.panelOpen,"devsite-concierge-container ":!0,"mobile-view-not-enabled":!this.Mk})}">
      ${tFa(this)} ${(0,_ds.N)`<div class="devsite-concierge-panel">
      ${UT(this,"devsite-concierge-info-panel",this.ft)}
      ${UT(this,"devsite-concierge-ai-panel",this.Zs)}
      ${UT(this,"devsite-concierge-recommendations-panel",this.qt)}
      ${UT(this,"devsite-concierge-api-explorer-panel",this.bt)}
      ${UT(this,"devsite-concierge-my-activity-panel",this.jt)}
    </div>`}
    </div>`}};WT.prototype.attributeChangedCallback=WT.prototype.attributeChangedCallback;WT.getTagName=OT;_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Zs",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"bt",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"ft",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"jt",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"qt",void 0);
_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Mg",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Xw",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Mk",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"pk",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"qk",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"ql",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Fl",void 0);
_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Ml",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Lm",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Om",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Xn",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Mo",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Xo",void 0);_ds.y([_ds.I(),_ds.z("design:type",Object)],WT.prototype,"Ud",void 0);
_ds.y([_ds.G({type:Boolean}),_ds.z("design:type",Object)],WT.prototype,"largeViewport",void 0);_ds.y([_ds.G({type:Boolean}),_ds.z("design:type",Object)],WT.prototype,"panelOpen",void 0);try{customElements.define(OT(),WT)}catch(a){console.warn("Unrecognized DevSite custom element - DevsiteConcierge",a)};})(_ds_www);
