(function(_ds){var window=this;var K2=class extends _ds.Pv{constructor(){super(["devsite-dialog","devsite-dropdown-list","devsite-view-release-notes-dialog"]);this.Qy=!1;this.releaseNotes=new Map;this.dialog=null;this.path="";this.label="Release Notes";this.disableAutoOpen=!1}Wa(){return this}async connectedCallback(){super.connectedCallback();try{this.path||(this.path=await _ds.as(_ds.E().href)),this.releaseNotes=await _ds.Wt(this.path)}catch(a){}this.releaseNotes.size===0?this.remove():(this.Qy=!0,this.disableAutoOpen||location.hash!==
"#release__notes"||this.o())}disconnectedCallback(){super.disconnectedCallback();let a;(a=this.dialog)==null||a.remove();this.dialog=null}o(a){a&&(a.preventDefault(),a.stopPropagation());let b;(b=this.dialog)==null||b.remove();this.dialog=document.createElement("devsite-dialog");this.dialog.classList.add("devsite-view-release-notes-dialog-container");_ds.Xu((0,_ds.N)`
      <devsite-view-release-notes-dialog
        .releaseNotes=${this.releaseNotes}>
      </devsite-view-release-notes-dialog>
    `,this.dialog);document.body.appendChild(this.dialog);this.dialog.open=!0;this.Da({category:"Site-Wide Custom Events",action:"release notes: view note",label:`${this.path}`})}render(){if(!this.Qy)return delete this.dataset.shown,(0,_ds.N)``;this.dataset.shown="";return(0,_ds.N)`
      <button class="view-notes-button" @click="${this.o}">
        ${this.label}
      </button>
    `}};_ds.y([_ds.I(),_ds.z("design:type",Object)],K2.prototype,"Qy",void 0);_ds.y([_ds.G({type:String}),_ds.z("design:type",Object)],K2.prototype,"path",void 0);_ds.y([_ds.G({type:String}),_ds.z("design:type",Object)],K2.prototype,"label",void 0);_ds.y([_ds.G({type:Boolean,Ha:"disable-auto-open"}),_ds.z("design:type",Object)],K2.prototype,"disableAutoOpen",void 0);try{customElements.define("devsite-view-release-notes",K2)}catch(a){console.warn("devsite.app.customElement.DevsiteViewReleaseNotes",a)};})(_ds_www);
