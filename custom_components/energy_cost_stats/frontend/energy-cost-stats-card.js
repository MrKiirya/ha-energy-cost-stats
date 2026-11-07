var G=globalThis,j=G.ShadowRoot&&(G.ShadyCSS===void 0||G.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,gt=Symbol(),Ot=new WeakMap,O=class{constructor(t,e,r){if(this._$cssResult$=!0,r!==gt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(j&&t===void 0){let r=e!==void 0&&e.length===1;r&&(t=Ot.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),r&&Ot.set(e,t))}return t}toString(){return this.cssText}},Lt=s=>new O(typeof s=="string"?s:s+"",void 0,gt),L=(s,...t)=>{let e=s.length===1?s[0]:t.reduce((r,n,i)=>r+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+s[i+1],s[0]);return new O(e,s,gt)},Ht=(s,t)=>{if(j)s.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let r=document.createElement("style"),n=G.litNonce;n!==void 0&&r.setAttribute("nonce",n),r.textContent=e.cssText,s.appendChild(r)}},_t=j?s=>s:s=>s instanceof CSSStyleSheet?(t=>{let e="";for(let r of t.cssRules)e+=r.cssText;return Lt(e)})(s):s;var{is:ve,defineProperty:ye,getOwnPropertyDescriptor:$e,getOwnPropertyNames:be,getOwnPropertySymbols:we,getPrototypeOf:xe}=Object,Z=globalThis,Ut=Z.trustedTypes,Se=Ut?Ut.emptyScript:"",ke=Z.reactiveElementPolyfillSupport,H=(s,t)=>s,ft={toAttribute(s,t){switch(t){case Boolean:s=s?Se:null;break;case Object:case Array:s=s==null?s:JSON.stringify(s)}return s},fromAttribute(s,t){let e=s;switch(t){case Boolean:e=s!==null;break;case Number:e=s===null?null:Number(s);break;case Object:case Array:try{e=JSON.parse(s)}catch{e=null}}return e}},zt=(s,t)=>!ve(s,t),It={attribute:!0,type:String,converter:ft,reflect:!1,useDefault:!1,hasChanged:zt};Symbol.metadata??=Symbol("metadata"),Z.litPropertyMetadata??=new WeakMap;var w=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=It){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let r=Symbol(),n=this.getPropertyDescriptor(t,r,e);n!==void 0&&ye(this.prototype,t,n)}}static getPropertyDescriptor(t,e,r){let{get:n,set:i}=$e(this.prototype,t)??{get(){return this[e]},set(a){this[e]=a}};return{get:n,set(a){let d=n?.call(this);i?.call(this,a),this.requestUpdate(t,d,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??It}static _$Ei(){if(this.hasOwnProperty(H("elementProperties")))return;let t=xe(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(H("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(H("properties"))){let e=this.properties,r=[...be(e),...we(e)];for(let n of r)this.createProperty(n,e[n])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[r,n]of e)this.elementProperties.set(r,n)}this._$Eh=new Map;for(let[e,r]of this.elementProperties){let n=this._$Eu(e,r);n!==void 0&&this._$Eh.set(n,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let r=new Set(t.flat(1/0).reverse());for(let n of r)e.unshift(_t(n))}else t!==void 0&&e.push(_t(t));return e}static _$Eu(t,e){let r=e.attribute;return r===!1?void 0:typeof r=="string"?r:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let r of e.keys())this.hasOwnProperty(r)&&(t.set(r,this[r]),delete this[r]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Ht(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,r){this._$AK(t,r)}_$ET(t,e){let r=this.constructor.elementProperties.get(t),n=this.constructor._$Eu(t,r);if(n!==void 0&&r.reflect===!0){let i=(r.converter?.toAttribute!==void 0?r.converter:ft).toAttribute(e,r.type);this._$Em=t,i==null?this.removeAttribute(n):this.setAttribute(n,i),this._$Em=null}}_$AK(t,e){let r=this.constructor,n=r._$Eh.get(t);if(n!==void 0&&this._$Em!==n){let i=r.getPropertyOptions(n),a=typeof i.converter=="function"?{fromAttribute:i.converter}:i.converter?.fromAttribute!==void 0?i.converter:ft;this._$Em=n;let d=a.fromAttribute(e,i.type);this[n]=d??this._$Ej?.get(n)??d,this._$Em=null}}requestUpdate(t,e,r,n=!1,i){if(t!==void 0){let a=this.constructor;if(n===!1&&(i=this[t]),r??=a.getPropertyOptions(t),!((r.hasChanged??zt)(i,e)||r.useDefault&&r.reflect&&i===this._$Ej?.get(t)&&!this.hasAttribute(a._$Eu(t,r))))return;this.C(t,e,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:r,reflect:n,wrapped:i},a){r&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,a??e??this[t]),i!==!0||a!==void 0)||(this._$AL.has(t)||(this.hasUpdated||r||(e=void 0),this._$AL.set(t,e)),n===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,i]of this._$Ep)this[n]=i;this._$Ep=void 0}let r=this.constructor.elementProperties;if(r.size>0)for(let[n,i]of r){let{wrapped:a}=i,d=this[n];a!==!0||this._$AL.has(n)||d===void 0||this.C(n,void 0,i,d)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(e)):this._$EM()}catch(r){throw t=!1,this._$EM(),r}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[H("elementProperties")]=new Map,w[H("finalized")]=new Map,ke?.({ReactiveElement:w}),(Z.reactiveElementVersions??=[]).push("2.1.2");var yt=globalThis,Bt=s=>s,Y=yt.trustedTypes,qt=Y?Y.createPolicy("lit-html",{createHTML:s=>s}):void 0,$t="$lit$",x=`lit$${Math.random().toFixed(9).slice(2)}$`,bt="?"+x,Ce=`<${bt}>`,A=document,I=()=>A.createComment(""),z=s=>s===null||typeof s!="object"&&typeof s!="function",wt=Array.isArray,Zt=s=>wt(s)||typeof s?.[Symbol.iterator]=="function",vt=`[ 	
\f\r]`,U=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ft=/-->/g,Kt=/>/g,k=RegExp(`>|${vt}(?:([^\\s"'>=/]+)(${vt}*=${vt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Vt=/'/g,Gt=/"/g,Yt=/^(?:script|style|textarea|title)$/i,xt=s=>(t,...e)=>({_$litType$:s,strings:t,values:e}),h=xt(1),Qe=xt(2),Je=xt(3),f=Symbol.for("lit-noChange"),p=Symbol.for("lit-nothing"),jt=new WeakMap,C=A.createTreeWalker(A,129);function Wt(s,t){if(!wt(s)||!s.hasOwnProperty("raw"))throw Error("invalid template strings array");return qt!==void 0?qt.createHTML(t):t}var Qt=(s,t)=>{let e=s.length-1,r=[],n,i=t===2?"<svg>":t===3?"<math>":"",a=U;for(let d=0;d<e;d++){let c=s[d],o,l,u=-1,m=0;for(;m<c.length&&(a.lastIndex=m,l=a.exec(c),l!==null);)m=a.lastIndex,a===U?l[1]==="!--"?a=Ft:l[1]!==void 0?a=Kt:l[2]!==void 0?(Yt.test(l[2])&&(n=RegExp("</"+l[2],"g")),a=k):l[3]!==void 0&&(a=k):a===k?l[0]===">"?(a=n??U,u=-1):l[1]===void 0?u=-2:(u=a.lastIndex-l[2].length,o=l[1],a=l[3]===void 0?k:l[3]==='"'?Gt:Vt):a===Gt||a===Vt?a=k:a===Ft||a===Kt?a=U:(a=k,n=void 0);let g=a===k&&s[d+1].startsWith("/>")?" ":"";i+=a===U?c+Ce:u>=0?(r.push(o),c.slice(0,u)+$t+c.slice(u)+x+g):c+x+(u===-2?d:g)}return[Wt(s,i+(s[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),r]},B=class s{constructor({strings:t,_$litType$:e},r){let n;this.parts=[];let i=0,a=0,d=t.length-1,c=this.parts,[o,l]=Qt(t,e);if(this.el=s.createElement(o,r),C.currentNode=this.el.content,e===2||e===3){let u=this.el.content.firstChild;u.replaceWith(...u.childNodes)}for(;(n=C.nextNode())!==null&&c.length<d;){if(n.nodeType===1){if(n.hasAttributes())for(let u of n.getAttributeNames())if(u.endsWith($t)){let m=l[a++],g=n.getAttribute(u).split(x),b=/([.?@])?(.*)/.exec(m);c.push({type:1,index:i,name:b[2],strings:g,ctor:b[1]==="."?Q:b[1]==="?"?J:b[1]==="@"?X:T}),n.removeAttribute(u)}else u.startsWith(x)&&(c.push({type:6,index:i}),n.removeAttribute(u));if(Yt.test(n.tagName)){let u=n.textContent.split(x),m=u.length-1;if(m>0){n.textContent=Y?Y.emptyScript:"";for(let g=0;g<m;g++)n.append(u[g],I()),C.nextNode(),c.push({type:2,index:++i});n.append(u[m],I())}}}else if(n.nodeType===8)if(n.data===bt)c.push({type:2,index:i});else{let u=-1;for(;(u=n.data.indexOf(x,u+1))!==-1;)c.push({type:7,index:i}),u+=x.length-1}i++}}static createElement(t,e){let r=A.createElement("template");return r.innerHTML=t,r}};function E(s,t,e=s,r){if(t===f)return t;let n=r!==void 0?e._$Co?.[r]:e._$Cl,i=z(t)?void 0:t._$litDirective$;return n?.constructor!==i&&(n?._$AO?.(!1),i===void 0?n=void 0:(n=new i(s),n._$AT(s,e,r)),r!==void 0?(e._$Co??=[])[r]=n:e._$Cl=n),n!==void 0&&(t=E(s,n._$AS(s,t.values),n,r)),t}var W=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:r}=this._$AD,n=(t?.creationScope??A).importNode(e,!0);C.currentNode=n;let i=C.nextNode(),a=0,d=0,c=r[0];for(;c!==void 0;){if(a===c.index){let o;c.type===2?o=new D(i,i.nextSibling,this,t):c.type===1?o=new c.ctor(i,c.name,c.strings,this,t):c.type===6&&(o=new tt(i,this,t)),this._$AV.push(o),c=r[++d]}a!==c?.index&&(i=C.nextNode(),a++)}return C.currentNode=A,n}p(t){let e=0;for(let r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(t,r,e),e+=r.strings.length-2):r._$AI(t[e])),e++}},D=class s{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,r,n){this.type=2,this._$AH=p,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=r,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=E(this,t,e),z(t)?t===p||t==null||t===""?(this._$AH!==p&&this._$AR(),this._$AH=p):t!==this._$AH&&t!==f&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Zt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==p&&z(this._$AH)?this._$AA.nextSibling.data=t:this.T(A.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:r}=t,n=typeof r=="number"?this._$AC(t):(r.el===void 0&&(r.el=B.createElement(Wt(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===n)this._$AH.p(e);else{let i=new W(n,this),a=i.u(this.options);i.p(e),this.T(a),this._$AH=i}}_$AC(t){let e=jt.get(t.strings);return e===void 0&&jt.set(t.strings,e=new B(t)),e}k(t){wt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,r,n=0;for(let i of t)n===e.length?e.push(r=new s(this.O(I()),this.O(I()),this,this.options)):r=e[n],r._$AI(i),n++;n<e.length&&(this._$AR(r&&r._$AB.nextSibling,n),e.length=n)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let r=Bt(t).nextSibling;Bt(t).remove(),t=r}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},T=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,r,n,i){this.type=1,this._$AH=p,this._$AN=void 0,this.element=t,this.name=e,this._$AM=n,this.options=i,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=p}_$AI(t,e=this,r,n){let i=this.strings,a=!1;if(i===void 0)t=E(this,t,e,0),a=!z(t)||t!==this._$AH&&t!==f,a&&(this._$AH=t);else{let d=t,c,o;for(t=i[0],c=0;c<i.length-1;c++)o=E(this,d[r+c],e,c),o===f&&(o=this._$AH[c]),a||=!z(o)||o!==this._$AH[c],o===p?t=p:t!==p&&(t+=(o??"")+i[c+1]),this._$AH[c]=o}a&&!n&&this.j(t)}j(t){t===p?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Q=class extends T{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===p?void 0:t}},J=class extends T{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==p)}},X=class extends T{constructor(t,e,r,n,i){super(t,e,r,n,i),this.type=5}_$AI(t,e=this){if((t=E(this,t,e,0)??p)===f)return;let r=this._$AH,n=t===p&&r!==p||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,i=t!==p&&(r===p||n);n&&this.element.removeEventListener(this.name,this,r),i&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},tt=class{constructor(t,e,r){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(t){E(this,t)}},Jt={M:$t,P:x,A:bt,C:1,L:Qt,R:W,D:Zt,V:E,I:D,H:T,N:J,U:X,B:Q,F:tt},Ae=yt.litHtmlPolyfillSupport;Ae?.(B,D),(yt.litHtmlVersions??=[]).push("3.3.3");var Xt=(s,t,e)=>{let r=e?.renderBefore??t,n=r._$litPart$;if(n===void 0){let i=e?.renderBefore??null;r._$litPart$=n=new D(t.insertBefore(I(),i),i,void 0,e??{})}return n._$AI(s),n};var St=globalThis,$=class extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Xt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return f}};$._$litElement$=!0,$.finalized=!0,St.litElementHydrateSupport?.({LitElement:$});var Ee=St.litElementPolyfillSupport;Ee?.({LitElement:$});(St.litElementVersions??=[]).push("4.2.2");var R={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},te=s=>(...t)=>({_$litDirective$:s,values:t}),et=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,r){this._$Ct=t,this._$AM=e,this._$Ci=r}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var{I:hr}=Jt;var ee=s=>s.strings===void 0;var Te={},re=(s,t=Te)=>s._$AH=t;var rt=te(class extends et{constructor(s){if(super(s),s.type!==R.PROPERTY&&s.type!==R.ATTRIBUTE&&s.type!==R.BOOLEAN_ATTRIBUTE)throw Error("The `live` directive is not allowed on child or event bindings");if(!ee(s))throw Error("`live` bindings can only contain a single expression")}render(s){return s}update(s,[t]){if(t===f||t===p)return t;let e=s.element,r=s.name;if(s.type===R.PROPERTY){if(t===e[r])return f}else if(s.type===R.BOOLEAN_ATTRIBUTE){if(!!t===e.hasAttribute(r))return f}else if(s.type===R.ATTRIBUTE&&e.getAttribute(r)===t+"")return f;return re(s),t}});var F=["today","yesterday","this_week","last_week","this_month","last_month","this_quarter","this_year","now-7d","now-30d","now-12m"];function v(s){let t=/^(\d{4})-(\d{2})-(\d{2})$/.exec(s);if(!t)throw new Error(`invalid date: ${s}`);let[,e,r,n]=t;return new Date(Date.UTC(Number(e),Number(r)-1,Number(n)))}function st(s){return s.toISOString().slice(0,10)}function Ct(s){try{return st(v(s))===s}catch{return!1}}function _(s,t){return st(new Date(v(s).getTime()+t*864e5))}function M(s,t=0){let e=v(s);return st(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t,1)))}function P(s,t=0){let e=v(s);return st(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t+1,0)))}function kt(s){let t=(v(s).getUTCDay()+6)%7;return _(s,-t)}function K(s){return Math.round((v(s.end).getTime()-v(s.start).getTime())/864e5)+1}function At(s){let t=v(s.start);if(t.getUTCDate()!==1||P(s.end)!==s.end)return null;let e=v(s.end);return(e.getUTCFullYear()-t.getUTCFullYear())*12+(e.getUTCMonth()-t.getUTCMonth())+1}function nt(s,t=new Date){let e={year:"numeric",month:"2-digit",day:"2-digit"},r;try{r=new Intl.DateTimeFormat("en-CA",{...e,timeZone:s}).formatToParts(t)}catch{r=new Intl.DateTimeFormat("en-CA",e).formatToParts(t)}let n=i=>r.find(a=>a.type===i)?.value??"";return`${n("year")}-${n("month")}-${n("day")}`}function S(s,t){switch(s){case"today":return{start:t,end:t};case"yesterday":{let e=_(t,-1);return{start:e,end:e}}case"this_week":{let e=kt(t);return{start:e,end:_(e,6)}}case"last_week":{let e=_(kt(t),-7);return{start:e,end:_(e,6)}}case"this_month":return{start:M(t),end:P(t)};case"last_month":return{start:M(t,-1),end:P(t,-1)};case"this_quarter":{let e=v(t).getUTCMonth(),r=M(t,-(e%3));return{start:r,end:P(r,2)}}case"this_year":{let e=t.slice(0,4);return{start:`${e}-01-01`,end:`${e}-12-31`}}case"now-7d":return{start:_(t,-6),end:t};case"now-30d":return{start:_(t,-29),end:t};case"now-12m":return{start:M(t,-11),end:P(t)}}}function Et(s){let t=At(s);if(t!==null){let r=v(s.start).getUTCMonth();return t===1?"month":t===3&&r%3===0?"quarter":t===12&&r===0?"year":"months"}let e=K(s);return e===1?"day":e===7&&kt(s.start)===s.start?"week":"days"}function Tt(s,t){let e=At(s);if(e!==null){let n=e*t;return{start:M(s.start,n),end:P(s.end,n)}}let r=K(s)*t;return{start:_(s.start,r),end:_(s.end,r)}}function se(s,t){switch(Et(s)){case"day":return S("today",t);case"week":return S("this_week",t);case"month":return S("this_month",t);case"quarter":return S("this_quarter",t);case"year":return S("this_year",t);case"months":{let r=At(s)??1;return{start:M(t,-(r-1)),end:P(t)}}case"days":return{start:_(t,-(K(s)-1)),end:t}}}function it(s,t){return s.start<=t&&t<=s.end}function q(s){return _(s.end,1)}function ot(s,t,e=new Date){let r=nt(t,e);if(!it(s,r))return q(s);let n;try{n=new Intl.DateTimeFormat("en-GB",{timeZone:t,hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(e)}catch{return q(s)}let i=Number(n.find(o=>o.type==="hour")?.value),a=Number(n.find(o=>o.type==="minute")?.value);if(!Number.isFinite(i)||a!==e.getUTCMinutes())return q(s);let d=s.start===r?Math.max(i,1):i,c=Re(t,e,d-i);return`${r}T${String(d).padStart(2,"0")}:00:00${c}`}function Re(s,t,e){let r=new Date(t.getTime()+e*36e5),n=new Intl.DateTimeFormat("en-US",{timeZone:s,timeZoneName:"longOffset"}).formatToParts(r).find(a=>a.type==="timeZoneName")?.value??"GMT",i=/^GMT([+-]\d{2}):?(\d{2})?$/.exec(n);return i?`${i[1]}:${i[2]??"00"}`:"+00:00"}var Pe=31;function ne(s){let t=K(s);return t<=2?"hour":t<=45?"day":t<=120?"week":"month"}function at(s,t){return s!=="hour"||K(t)<=Pe}var De={title:"Energy cost",previous:"Previous",next:"Next",now:"Now",refresh:"Refresh",menu:"Menu",period:"Period",custom:"Custom period",from:"From",to:"To",apply:"Apply",grouping:"Grouping","grouping.auto":"Auto","grouping.hour":"Hours","grouping.day":"Days","grouping.week":"Weeks","grouping.month":"Months","grouping.hour_too_long":"Hours: up to 31 days","preset.today":"Today","preset.yesterday":"Yesterday","preset.this_week":"This week","preset.last_week":"Last week","preset.this_month":"This month","preset.last_month":"Last month","preset.this_quarter":"This quarter","preset.this_year":"This year","preset.now-7d":"Last 7 days","preset.now-30d":"Last 30 days","preset.now-12m":"Last 12 months",device:"Device",total:"Total",kwh:"kWh",cost:"Cost",avg_price:"Avg. price","sort.by":"Sort by {column}, {direction}","sort.ascending":"ascending","sort.descending":"descending","sort.cost_of":"{zone} cost","sort.total_cost":"total cost",breakdown:"By period",breakdown_device:"Show",all_devices:"All devices",data_quality:"Data quality",loading:"Loading…",no_devices:"No energy sensors selected. Add them in the integration options.",no_plan:"No tariff plan covers this period: costs are unknown.",unpriced:"{hours} h before the first tariff plan are not priced.","status.complete":"Complete","status.estimated":"Contains estimated hours (spread over a data gap)","status.partial":"Some hours are missing","status.missing":"No data","issue.estimated":"estimated","issue.excluded_negative":"excluded (negative)","issue.excluded_spike":"excluded (spike)","statistics.no_statistics":"no statistics yet","statistics.unsupported":"unsupported sensor","error.not_loaded":"Energy Cost Stats is not set up or not loaded.","error.invalid_period":"Invalid period.","error.period_too_long":"The period is too long for this grouping.","error.unknown_entity":"The card lists a sensor that is not selected in the integration.","error.unknown_command":"The integration is not loaded (restart Home Assistant after installing).","error.generic":"Could not load the report: {message}","compare.title":"Tariff comparison","compare.tariff":"Tariff","compare.actual":"Actual","compare.difference":"Difference","compare.empty":"No tariffs to compare. Choose them in the integration options (Configure → Compare).","compare.unpriced":"{hours} h not priced by this tariff — the difference covers only the priced hours","compare.unpriced_actual":"{hours} h not priced by the actual schedule — the difference covers only the priced hours","compare.error":"Could not load the comparison: {message}","error.unknown_tariff":"A tariff in the comparison list is not defined in the integration.","nested.title":"Measured inside {name}; not counted again in the total","nested.note":"Indented rows are measured inside the device above them. The total counts their energy only for hours where the device above has no data.",coverage:"{measured} measured, {estimated} estimated, {excluded} excluded, {missing} missing of {expected} h"},Me={title:"Стоимость электроэнергии",previous:"Назад",next:"Вперёд",now:"Сейчас",refresh:"Обновить",menu:"Меню",period:"Период",custom:"Свой период",from:"С",to:"По",apply:"Применить",grouping:"Группировка","grouping.auto":"Авто","grouping.hour":"По часам","grouping.day":"По дням","grouping.week":"По неделям","grouping.month":"По месяцам","grouping.hour_too_long":"По часам: до 31 дня","preset.today":"Сегодня","preset.yesterday":"Вчера","preset.this_week":"Эта неделя","preset.last_week":"Прошлая неделя","preset.this_month":"Этот месяц","preset.last_month":"Прошлый месяц","preset.this_quarter":"Этот квартал","preset.this_year":"Этот год","preset.now-7d":"Последние 7 дней","preset.now-30d":"Последние 30 дней","preset.now-12m":"Последние 12 месяцев",device:"Устройство",total:"Итого",kwh:"кВт·ч",cost:"Сумма",avg_price:"Ср. цена","sort.by":"Сортировать по: {column}, {direction}","sort.ascending":"по возрастанию","sort.descending":"по убыванию","sort.cost_of":"стоимость {zone}","sort.total_cost":"общая стоимость",breakdown:"По периодам",breakdown_device:"Показать",all_devices:"Все устройства",data_quality:"Качество данных",loading:"Загрузка…",no_devices:"Не выбраны датчики энергии. Добавьте их в настройках интеграции.",no_plan:"Для этого периода нет тарифного плана: стоимость неизвестна.",unpriced:"{hours} ч до первого тарифного плана не оценены.","status.complete":"Полные данные","status.estimated":"Есть оценочные часы (распределены по пропуску)","status.partial":"Часть часов отсутствует","status.missing":"Нет данных","issue.estimated":"оценка","issue.excluded_negative":"исключено (отрицательное)","issue.excluded_spike":"исключено (выброс)","statistics.no_statistics":"статистики пока нет","statistics.unsupported":"датчик не поддерживается","error.not_loaded":"Energy Cost Stats не настроена или не загружена.","error.invalid_period":"Неверный период.","error.period_too_long":"Период слишком длинный для этой группировки.","error.unknown_entity":"В карточке указан датчик, не выбранный в интеграции.","error.unknown_command":"Интеграция не загружена (перезапустите Home Assistant после установки).","error.generic":"Не удалось загрузить отчёт: {message}","compare.title":"Сравнение тарифов","compare.tariff":"Тариф","compare.actual":"Фактически","compare.difference":"Разница","compare.empty":"Нет тарифов для сравнения. Выберите их в настройках интеграции (Настроить → Сравнение тарифов).","compare.unpriced":"{hours} ч не оценены этим тарифом — разница учитывает только оценённые часы","compare.unpriced_actual":"{hours} ч не оценены фактическим расписанием — разница учитывает только оценённые часы","compare.error":"Не удалось загрузить сравнение: {message}","error.unknown_tariff":"Тариф из списка сравнения не определён в интеграции.","nested.title":"Измеряется внутри «{name}»; в итоге повторно не учитывается","nested.note":"Строки со сдвигом измеряются внутри устройства выше. Итог учитывает их энергию только за часы, когда у устройства выше нет данных.",coverage:"{measured} измерено, {estimated} оценено, {excluded} исключено, {missing} нет из {expected} ч"},N=class{constructor(t){this.locale=t||"en",this.table=this.locale.toLowerCase().startsWith("ru")?Me:De}t(t,e={}){return this.table[t].replace(/\{(\w+)\}/g,(r,n)=>n in e?String(e[n]):`{${n}}`)}preset(t){return this.t(`preset.${t}`)}grouping(t){return this.t(`grouping.${t}`)}number(t,e){return t==null?"—":new Intl.NumberFormat(this.locale,{minimumFractionDigits:e,maximumFractionDigits:e}).format(Number(t))}money(t,e,r=!1){if(t==null)return"—";if(e)try{return new Intl.NumberFormat(this.locale,{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:2,...r?{signDisplay:"exceptZero"}:{}}).format(Number(t))}catch{}return r?new Intl.NumberFormat(this.locale,{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero"}).format(Number(t)):this.number(t,2)}signedMoney(t,e){return t===null?"—":this.money(String(t),e,!0)}signedPercent(t){return t===null?"—":`${new Intl.NumberFormat(this.locale,{minimumFractionDigits:1,maximumFractionDigits:1,signDisplay:"exceptZero"}).format(t)} %`}avgPrice(t,e){return t===null||e===null||Number(e)===0?"—":this.number(String(Number(t)/Number(e)),2)}date(t,e){return new Intl.DateTimeFormat(this.locale,{...e,timeZone:"UTC"}).format(new Date(`${t}T00:00:00Z`))}periodLabel(t){switch(Et(t)){case"day":return this.date(t.start,{day:"numeric",month:"long",year:"numeric"});case"month":return this.date(t.start,{month:"long",year:"numeric"});case"quarter":return`Q${Math.floor(Number(t.start.slice(5,7))/3)+1} ${t.start.slice(0,4)}`;case"year":return t.start.slice(0,4);case"months":return`${this.date(t.start,{month:"short",year:"numeric"})} – ${this.date(t.end,{month:"short",year:"numeric"})}`;default:{let r=t.start.slice(0,4)===t.end.slice(0,4),n=this.date(t.start,{day:"numeric",month:"short",...r?{}:{year:"numeric"}}),i=this.date(t.end,{day:"numeric",month:"short",year:"numeric"});return`${n} – ${i}`}}}bucketLabel(t,e){let r=t.slice(0,10);switch(e){case"hour":return`${this.date(r,{day:"numeric",month:"short"})} ${t.slice(11,16)}`;case"day":return this.date(r,{weekday:"short",day:"numeric",month:"short"});case"week":return this.date(r,{day:"numeric",month:"short",year:"numeric"});case"month":return this.date(r,{month:"long",year:"numeric"});default:return this.t("total")}}};function ie(s,t){if(s===null||t===null)return{amount:null,percent:null};let e=Number(s),r=Number(t);if(!Number.isFinite(e)||!Number.isFinite(r))return{amount:null,percent:null};let n=r-e;return{amount:n,percent:e===0?null:n/e*100}}function oe(s,t){let e=new Set(s.map(c=>c.entity_id)),r=new Map,n=[];for(let c of s){let o=c.upstream;if(o&&o!==c.entity_id&&e.has(o)){let l=r.get(o)??[];l.push(c.entity_id),r.set(o,l)}else n.push(c.entity_id)}if(t){n.sort(t);for(let c of r.values())c.sort(t)}let i=[],a=new Set,d=(c,o)=>{if(!a.has(c)){a.add(c),i.push({entity_id:c,depth:o});for(let l of r.get(c)??[])d(l,o+1)}};for(let c of n)d(c,0);for(let c of s)d(c.entity_id,0);return i}function ct(s,t){return t===void 0||s===void 0?s!==t:s.language!==t.language||s.locale?.language!==t.locale?.language||s.config?.time_zone!==t.config?.time_zone}var Ne=["name","total","avg_price"],lt={sort:"total",direction:"desc"};function ut(s){return s==="name"?"asc":"desc"}function ae(s,t){if(s!==void 0&&(typeof s!="string"||s===""))throw new Error("sort must be name, total, avg_price or a zone key");if(t!==void 0&&t!=="asc"&&t!=="desc")throw new Error(`sort_direction must be asc or desc, not ${String(t)}`)}function ce(s,t){return Ne.includes(s.sort)||t.includes(s.sort)?s:lt}function dt(s){if(s==null)return null;let t=Number(s);return Number.isFinite(t)?t:null}function Oe(s,t){if(t==="total")return dt(s.cost);if(t==="avg_price"){let r=dt(s.cost),n=dt(s.kwh);if(r===null||n===null||n<=0)return null;let i=r/n;return Number.isFinite(i)?i:null}let e=s.zones.find(r=>r.key===t);return e?dt(e.cost):null}function de(s,t,e,r){let n=new Intl.Collator(r,{sensitivity:"base",numeric:!0}),i=s.direction==="asc"?1:-1,a=o=>e.get(o)??o,d=(o,l)=>n.compare(a(o),a(l))||(o<l?-1:o>l?1:0);if(s.sort==="name")return(o,l)=>{let u=n.compare(a(o),a(l));return u!==0?i*u:o<l?-1:o>l?1:0};let c=o=>{let l=t.get(o);return l?Oe(l,s.sort):null};return(o,l)=>{let u=c(o),m=c(l);return u!==null&&m!==null&&u!==m?i*(u<m?-1:1):u===null&&m!==null?1:u!==null&&m===null?-1:d(o,l)}}function le(s,t){let e=JSON.stringify([t.title??null,t.entities??null,t.sort??null,t.sort_direction??null]);return`energy-cost-stats-card.sort.v1|${s}|${e}`}function ue(s){try{let t=localStorage.getItem(s);if(!t)return;let e=JSON.parse(t);if(e&&typeof e.sort=="string"&&e.sort!==""&&(e.direction==="asc"||e.direction==="desc"))return{sort:e.sort,direction:e.direction}}catch{}}function pe(s,t){try{localStorage.setItem(s,JSON.stringify(t))}catch{}}var Le="energy_cost_stats/report",He="energy_cost_stats/compare";function he(s,t){let e={type:s,start:t.period.start,end:ot(t.period,t.timeZone,t.now)};return t.entities&&t.entities.length>0&&(e.entities=t.entities),e}function Ue(s){let{type:t,start:e,end:r,entities:n}=he(Le,s),i={type:t,start:e,end:r,grouping:s.grouping};return n!==void 0&&(i.entities=n),i}function Ie(s){return he(He,s)}function me(s,t){return s.callWS(Ie(t))}function ge(s,t){return s.callWS(Ue(t))}function pt(s){if(s&&typeof s=="object"&&"code"in s){let t=s.code;return typeof t=="string"?t:void 0}}function Rt(s){return s&&typeof s=="object"&&"message"in s?String(s.message):String(s)}var y="energy-cost-stats-card",_e=["auto","hour","day","week","month"],ze=600*1e3,Be="M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",qe="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",Fe="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";function Pt(s){return h`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${s}></path></svg>`}var ht=class extends ${constructor(){super(...arguments);this._groupingChoice="auto";this._compareLoading=!1;this._compareHidden=!1;this._loading=!1;this._customOpen=!1;this._customStart="";this._customEnd="";this._breakdownEntity="";this._storageKey="";this._requestSeq=0;this._compareSeq=0;this._lastRequestOpen=!1}static{this.properties={hass:{attribute:!1,hasChanged:ct},_config:{state:!0},_period:{state:!0},_groupingChoice:{state:!0},_report:{state:!0},_compare:{state:!0},_compareError:{state:!0},_compareLoading:{state:!0},_compareHidden:{state:!0},_error:{state:!0},_loading:{state:!0},_customOpen:{state:!0},_customStart:{state:!0},_customEnd:{state:!0},_breakdownEntity:{state:!0},_sortChoice:{state:!0}}}static getStubConfig(){return{type:`custom:${y}`,period:"this_month"}}setConfig(e){if(!e||typeof e!="object")throw new Error("Invalid configuration");if(e.period!==void 0&&!F.includes(e.period))throw new Error(`Unknown period: ${String(e.period)}`);if(e.grouping!==void 0&&!_e.includes(e.grouping))throw new Error(`Unknown grouping: ${String(e.grouping)}`);if(e.entities!==void 0&&(!Array.isArray(e.entities)||e.entities.some(n=>typeof n!="string")))throw new Error("entities must be a list of entity ids");ae(e.sort,e.sort_direction);let r=this._config;this._config=e,this._storageKey=le(globalThis.location?.pathname??"",e),this._sortChoice=ue(this._storageKey),this._groupingChoice=e.grouping??"auto",r&&this._period&&(this._period=void 0,this._report=void 0,this._compare=void 0)}getCardSize(){let e=this._compare&&!this._compareHidden?this._compare.tariffs.length+3:0;return 3+(this._report?.devices.length??2)+e}getGridOptions(){return{columns:"full",min_columns:6}}get _strings(){return new N(this.hass?.locale?.language??this.hass?.language)}get _timeZone(){return this._reportTimeZone??this.hass?.config?.time_zone}_today(){return nt(this._timeZone)}get grouping(){let e=this._period;if(!e)return"day";let r=this._groupingChoice;return r!=="auto"&&at(r,e)?r:ne(e)}connectedCallback(){super.connectedCallback(),typeof ResizeObserver<"u"&&(this._controlsObserver=new ResizeObserver(e=>{let r=e[e.length-1];if(!r)return;let n=r.target.getBoundingClientRect().height;this.style.setProperty("--energy-cost-stats-controls-height",`${Math.ceil(n)}px`)})),this._observeControls(),this._timer=setInterval(()=>{this._period&&this._lastRequestOpen&&!this._loading&&this._load()},ze)}disconnectedCallback(){super.disconnectedCallback(),this._timer!==void 0&&clearInterval(this._timer),this._timer=void 0,this._controlsObserver?.disconnect(),this._controlsObserver=void 0,this._observedControls=void 0}_observeControls(){let e=this._controlsObserver;if(!e)return;let r=this.shadowRoot?.querySelector(".controls")??void 0;r!==this._observedControls&&(this._observedControls&&e.unobserve(this._observedControls),this._observedControls=r,r&&e.observe(r))}willUpdate(e){this.hass&&this._config&&!this._period&&(this._period=S(this._config.period??"this_month",this._today())),super.willUpdate(e)}updated(e){super.updated(e),this._observeControls(),!(!this.hass||!this._period)&&(e.has("_period")||e.has("hass")&&e.get("hass")===void 0?this._load():e.has("_groupingChoice")&&this._loadReport())}_load(){return this._loadCompare(),this._loadReport()}async _loadCompare(){let e=this.hass,r=this._period;if(!e||!r)return;let n=++this._compareSeq;this._compareLoading=!0;try{let i=await me(e,{period:r,entities:this._config?.entities,timeZone:this._timeZone});if(n!==this._compareSeq)return;this._compare=i,this._compareError=void 0,this._compareHidden=!1}catch(i){if(n!==this._compareSeq)return;if(this._compare=void 0,pt(i)==="unknown_command"){this._compareHidden=!0,this._compareError=void 0;return}this._compareHidden=!1,this._compareError=this._strings.t("compare.error",{message:this._errorMessage(i)})}finally{n===this._compareSeq&&(this._compareLoading=!1)}}_errorMessage(e){let r=pt(e),i=r?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_tariff:"error.unknown_tariff"}[r]:void 0;return i?this._strings.t(i):Rt(e)}async _loadReport(){let e=this.hass,r=this._period;if(!e||!r)return;let n=++this._requestSeq,i=this._timeZone;this._loading=!0;try{let a=await ge(e,{period:r,grouping:this.grouping,entities:this._config?.entities,timeZone:i});if(n!==this._requestSeq)return;this._report=a,this._error=void 0,this._reportTimeZone=a.time_zone,this._lastRequestOpen=ot(r,a.time_zone)!==q(r),a.time_zone!==i&&it(r,nt(a.time_zone))&&this._load()}catch(a){if(n!==this._requestSeq)return;let d=pt(a),o=d?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_command:"error.unknown_command"}[d]:void 0;this._error=o?this._strings.t(o):this._strings.t("error.generic",{message:Rt(a)}),this._report=void 0}finally{n===this._requestSeq&&(this._loading=!1)}}_selectedPreset(){if(!this._period)return"";let e=this._today(),r=this._period;return F.find(n=>{let i=S(n,e);return i.start===r.start&&i.end===r.end})??""}_onPreset(e){let r=e.target.value;if(r==="custom"){this._openCustom();return}F.includes(r)&&(this._customOpen=!1,this._period=S(r,this._today()))}_openCustom(){this._customOpen=!0,this._customStart=this._period?.start??this._today(),this._customEnd=this._period?.end??this._today()}_applyCustom(){let e=this._customStart,r=this._customEnd;!Ct(e)||!Ct(r)||(this._period=e<=r?{start:e,end:r}:{start:r,end:e},this._customOpen=!1)}_shift(e){this._period&&(this._period=Tt(this._period,e))}_now(){this._period&&(this._period=se(this._period,this._today()))}_onGrouping(e){this._groupingChoice=e.target.value}render(){if(!this._config||!this.hass||!this._period)return p;let e=this._strings,r=this._config.title??e.t("title");return h`
      <ha-card>
        ${r||this._loading?h`<div class="header">
              ${r?h`<div class="title">${r}</div>`:p}
              ${this._loading?h`<div class="loading" role="status">${e.t("loading")}</div>`:p}
            </div>`:p}
        <div class="controls">${this._renderPicker(e)}</div>
        <div class="content">
          ${this._error?h`<div class="error" role="alert">${this._error}</div>`:this._report?this._renderReport(e,this._report):p}
        </div>
      </ha-card>
    `}_renderPicker(e){let r=this._period,n=this._selectedPreset(),i=this._today(),a=it(r,i),d=Tt(r,1).start>i;return h`
      <div class="picker">
        <select
          class="preset"
          aria-label=${e.t("period")}
          .value=${rt(n)}
          @change=${this._onPreset}
        >
          <option value="" ?hidden=${n!==""} ?selected=${n===""}>
            ${e.t("custom")}
          </option>
          ${F.map(c=>h`<option value=${c} ?selected=${c===n}>${e.preset(c)}</option>`)}
          <option value="custom">${e.t("custom")}…</option>
        </select>
        <div class="nav">
          <button
            class="icon prev"
            title=${e.t("previous")}
            aria-label=${e.t("previous")}
            @click=${()=>this._shift(-1)}
          >
            ${Pt(Be)}
          </button>
          <button class="label" title=${e.t("custom")} @click=${this._openCustom}>
            ${e.periodLabel(r)}
          </button>
          <button
            class="icon next"
            title=${e.t("next")}
            aria-label=${e.t("next")}
            ?disabled=${d}
            @click=${()=>this._shift(1)}
          >
            ${Pt(qe)}
          </button>
          <button class="text now" ?disabled=${a} @click=${this._now}>
            ${e.t("now")}
          </button>
        </div>
        <button
          class="icon refresh"
          title=${e.t("refresh")}
          aria-label=${e.t("refresh")}
          @click=${()=>{this._load()}}
        >
          ${Pt(Fe)}
        </button>
      </div>
      ${this._customOpen?h`<div class="custom">
            <label
              >${e.t("from")}
              <input
                type="date"
                class="custom-start"
                .value=${this._customStart}
                max=${i}
                @change=${c=>{this._customStart=c.target.value}}
            /></label>
            <label
              >${e.t("to")}
              <input
                type="date"
                class="custom-end"
                .value=${this._customEnd}
                @change=${c=>{this._customEnd=c.target.value}}
            /></label>
            <button class="text apply" @click=${this._applyCustom}>${e.t("apply")}</button>
          </div>`:p}
    `}_activeSort(e){let r=this._config,n=r?.sort?{sort:r.sort,direction:r.sort_direction??ut(r.sort)}:r?.sort_direction?{sort:lt.sort,direction:r.sort_direction}:void 0,i=this._sortChoice??n??lt;return ce(i,e.zones.map(a=>a.key))}_onSort(e){if(!this._report)return;let r=this._activeSort(this._report),n=r.sort===e?r.direction==="asc"?"desc":"asc":ut(e);this._sortChoice={sort:e,direction:n},pe(this._storageKey,this._sortChoice)}_renderReport(e,r){if(r.devices.length===0)return h`<div class="note">${e.t("no_devices")}</div>`;let n=new Map(r.devices.map(d=>[d.entity_id,d])),i=r.totals,a=r.plans.length===0;return h`
      ${a?h`<div class="note warning">${e.t("no_plan")}</div>`:p}
      ${!a&&r.unpriced_hours>0?h`<div class="note warning">
            ${e.t("unpriced",{hours:r.unpriced_hours})}
          </div>`:p}
      <div class="table-wrap">
        <table class="devices">
          ${this._renderHead(e,r,e.t("device"),i,this._activeSort(r))}
          <tbody>
            ${this._deviceRows(r).map(({row:d,depth:c})=>{let o=d.entity_id?n.get(d.entity_id):void 0,l=o?.name??d.entity_id??"",u=o&&o.statistics!=="ok"?e.t(`statistics.${o.statistics}`):"",m=o?.upstream?n.get(o.upstream):void 0;return this._renderRow(e,r,d,l,u,{depth:c,title:c>0&&m?`${l} — ${e.t("nested.title",{name:m.name})}`:l})})}
          </tbody>
          <tfoot>
            ${this._renderRow(e,r,i.total,e.t("total"),"")}
          </tfoot>
        </table>
      </div>
      ${r.devices.some(d=>d.upstream&&n.has(d.upstream))?h`<div class="note nested-note">${e.t("nested.note")}</div>`:p}
      ${this._renderComparison(e,r)}
      ${r.grouping!=="total"?this._renderBreakdown(e,r):p}
      ${r.issues.length>0?this._renderIssues(e,r,n):p}
    `}_deviceRows(e){let r=new Map(e.totals.rows.map(o=>[o.entity_id,o])),n=new Map;for(let o of e.totals.rows)o.entity_id&&n.set(o.entity_id,o);let i=new Map(e.devices.map(o=>[o.entity_id,o.name])),a=de(this._activeSort(e),n,i,this._strings.locale),d=[],c=new Set;for(let{entity_id:o,depth:l}of oe(e.devices,a)){let u=r.get(o);u&&!c.has(u)&&(c.add(u),d.push({row:u,depth:l}))}for(let o of e.totals.rows)c.has(o)||d.push({row:o,depth:0});return d}_renderComparison(e,r){if(this._compareHidden)return p;let n=this._compare,i=this._compareError;if(!n&&!i)return p;let a=r.currency,d=p;if(i)d=h`<div class="error" role="alert">${i}</div>`;else if(n&&n.tariffs.length===0)d=h`<div class="note">${e.t("compare.empty")}</div>`;else if(n){let o=n.actual,l=o.totals.total,u=o.plans.map(m=>m.name).join(" → ");d=h`<div class="table-wrap">
        <table class="comparison">
          <thead>
            <tr>
              <th rowspan="2" class="name">${e.t("compare.tariff")}</th>
              <th rowspan="2" class="num">${e.t("cost")}</th>
              <th colspan="2" class="zone group-start">${e.t("compare.difference")}</th>
              <th rowspan="2" class="num group-start">${e.t("avg_price")}</th>
            </tr>
            <tr>
              <th class="num group-start">${a??""}</th>
              <th class="num">%</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row" class="name" title=${e.t("compare.actual")}>
                <span>${e.t("compare.actual")}</span>
                ${u?h`<span class="sub">${u}</span>`:p}
              </th>
              <td class="num strong">${e.money(l.cost,a)}</td>
              <td class="num group-start">—</td>
              <td class="num">—</td>
              <td class="num group-start">${e.avgPrice(l.cost,l.kwh)}</td>
            </tr>
            ${n.tariffs.map(m=>{let g=m.report.totals.total,b=ie(l.cost,g.cost),V=m.report.unpriced_hours,Nt=V||o.unpriced_hours,fe=e.t(V>0?"compare.unpriced":"compare.unpriced_actual",{hours:Nt});return h`<tr>
                <th scope="row" class="name" title=${m.name}>
                  <span>${m.name}</span>
                  ${Nt>0?h`<span class="badge partial" title=${fe}
                        >!</span
                      >`:p}
                </th>
                <td class="num strong">${e.money(g.cost,a)}</td>
                <td class="num group-start">${e.signedMoney(b.amount,a)}</td>
                <td class="num">${e.signedPercent(b.percent)}</td>
                <td class="num group-start">${e.avgPrice(g.cost,g.kwh)}</td>
              </tr>`})}
          </tbody>
        </table>
      </div>`}let c=this._compareLoading;return h`<section
      class="comparison ${c?"loading":""}"
      aria-busy=${c?"true":"false"}
    >
      <h3>
        ${e.t("compare.title")}
        ${c?h`<span class="loading" role="status">${e.t("loading")}</span>`:p}
      </h3>
      ${d}
    </section>`}_renderHead(e,r,n,i,a){let d=r.currency,c=(l,u,m)=>{if(!a)return m;let g=a.sort===l,b=g?a.direction==="asc"?"desc":"asc":ut(l),V=e.t("sort.by",{column:u,direction:e.t(b==="asc"?"sort.ascending":"sort.descending")});return h`<button
        type="button"
        class="sort"
        data-sort=${l}
        title=${V}
        @click=${()=>this._onSort(l)}
      >
        ${m}${g?h`<span class="sort-indicator" aria-hidden="true"
              >${a.direction==="asc"?"▲":"▼"}</span
            >`:p}
      </button>`},o=l=>a&&a.sort===l?a.direction==="asc"?"ascending":"descending":p;return h`
      <thead>
        <tr>
          <th rowspan="2" class="name" aria-sort=${o("name")}>
            ${c("name",n,n)}
          </th>
          ${r.zones.map((l,u)=>{let m=i.total.zones[u]?.price??null;return h`<th colspan="2" class="zone group-start" aria-sort=${o(l.key)}>
              ${c(l.key,e.t("sort.cost_of",{zone:l.name}),h`${l.name}${m!==null?h`<span class="price">${e.money(m,d)}</span>`:p}`)}
            </th>`})}
          <th colspan="2" class="zone sum group-start" aria-sort=${o("total")}>
            ${c("total",e.t("sort.total_cost"),e.t("total"))}
          </th>
          <th rowspan="2" class="num avg group-start" aria-sort=${o("avg_price")}>
            ${c("avg_price",e.t("avg_price"),e.t("avg_price"))}
          </th>
        </tr>
        <tr>
          ${r.zones.map(()=>h`<th class="num group-start">${e.t("kwh")}</th>
                <th class="num">${e.t("cost")}</th>`)}
          <th class="num group-start">${e.t("kwh")}</th>
          <th class="num">${e.t("cost")}</th>
        </tr>
      </thead>
    `}_renderRow(e,r,n,i,a,d={depth:0,title:i}){let c=r.currency,o=n.coverage,l=e.t("coverage",{measured:o.measured,estimated:o.estimated,excluded:o.excluded,missing:o.missing,expected:o.expected});return h`
      <tr class="status-${n.status} ${d.depth>0?"nested":""}">
        <th
          scope="row"
          class="name"
          title=${d.title}
          style=${d.depth>0?`--depth: ${d.depth}`:p}
        >
          <span>${d.depth>0?"↳ ":""}${i}</span>
          ${n.status!=="complete"?h`<span
                class="badge ${n.status}"
                title="${e.t(`status.${n.status}`)} · ${l}"
                >${n.status==="estimated"?"≈":"!"}</span
              >`:p}
          ${a?h`<span class="sub">${a}</span>`:p}
        </th>
        ${n.zones.map(u=>h`<td class="num group-start">${e.number(u.kwh,2)}</td>
              <td class="num">${e.money(u.cost,c)}</td>`)}
        <td class="num strong group-start">${e.number(n.kwh,2)}</td>
        <td class="num strong">${e.money(n.cost,c)}</td>
        <td class="num group-start">${e.avgPrice(n.cost,n.kwh)}</td>
      </tr>
    `}_renderBreakdown(e,r){let n=this._breakdownEntity,i=n?r.devices.findIndex(o=>o.entity_id===n):-1,a=o=>(i>=0?o.rows.find(l=>l.entity_id===n):void 0)??o.total,d=this._groupingChoice,c=d==="auto"||at(d,this._period)?d:"auto";return h`
      <details class="breakdown" ?open=${this._config?.show_breakdown??!1}>
        <summary>${e.t("breakdown")}</summary>
        <div class="breakdown-controls">
          <label
            >${e.t("breakdown_device")}
            <select
              class="breakdown-device"
              .value=${rt(i>=0?n:"")}
              @change=${o=>{this._breakdownEntity=o.target.value}}
            >
              <option value="">${e.t("all_devices")}</option>
              ${r.devices.map(o=>h`<option value=${o.entity_id} ?selected=${o.entity_id===n}>
                    ${o.name}
                  </option>`)}
            </select>
          </label>
          <label
            >${e.t("grouping")}
            <select class="grouping" .value=${rt(c)} @change=${this._onGrouping}>
              ${_e.map(o=>{let l=o==="auto"||at(o,this._period);return h`<option
                  value=${o}
                  ?disabled=${!l}
                  ?selected=${o===c}
                >
                  ${l?e.grouping(o):e.t("grouping.hour_too_long")}
                </option>`})}
            </select>
          </label>
        </div>
        <div class="table-wrap">
          <table class="buckets">
            ${this._renderHead(e,r,e.t("period"),r.totals)}
            <tbody>
              ${r.buckets.map(o=>this._renderRow(e,r,a(o),this._bucketLabel(e,r,o),""))}
            </tbody>
            <tfoot>
              ${this._renderRow(e,r,a(r.totals),e.t("total"),"")}
            </tfoot>
          </table>
        </div>
      </details>
    `}_bucketLabel(e,r,n){if(r.grouping==="week"){let i=n.start.slice(0,10);return e.periodLabel({start:i,end:_(i,6)})}return e.bucketLabel(n.start,r.grouping)}_renderIssues(e,r,n){return h`
      <details class="issues">
        <summary>${e.t("data_quality")} (${r.issues.length})</summary>
        <ul>
          ${r.issues.map(i=>h`<li>
                <span class="who">${n.get(i.entity_id)?.name??i.entity_id}</span>:
                ${e.t(`issue.${i.kind}`)},
                ${e.bucketLabel(i.start,"hour")} – ${e.bucketLabel(i.end,"hour")}
                (${i.hours} h, ${e.number(i.kwh,3)} ${e.t("kwh")})
              </li>`)}
        </ul>
      </details>
    `}static{this.styles=L`
    :host {
      display: block;
      /* Where the controls stick: below Home Assistant's top bar (override per theme / kiosk). */
      --ecs-sticky-top: var(
        --energy-cost-stats-sticky-top,
        calc(
          var(--header-height, 56px) + var(--safe-area-inset-top, env(safe-area-inset-top, 0px))
        )
      );
    }
    ha-card {
      padding: 12px 16px 16px;
      box-sizing: border-box;
    }
    .header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 8px;
    }
    .title {
      font-size: 1.25rem;
      font-weight: 500;
      line-height: 2;
    }
    .loading {
      color: var(--secondary-text-color);
      font-size: 0.85rem;
    }
    .controls {
      position: sticky;
      top: var(--ecs-sticky-top);
      /* Below Home Assistant's fixed header (z-index 4); above the table box. */
      z-index: 3;
      margin-inline: -16px;
      padding-inline: 16px;
      background: var(--ha-card-background, var(--card-background-color, white));
    }
    .picker,
    .custom,
    .breakdown-controls {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin: 4px 0 8px;
    }
    .nav {
      display: flex;
      align-items: center;
      gap: 2px;
      flex: 1 1 auto;
    }
    select,
    input,
    button {
      font: inherit;
      color: var(--primary-text-color);
    }
    select,
    input {
      background: var(--card-background-color, transparent);
      border: 1px solid var(--divider-color);
      border-radius: 6px;
      padding: 4px 6px;
    }
    button {
      background: none;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      padding: 4px 8px;
    }
    button:hover:not([disabled]) {
      background: var(--secondary-background-color);
    }
    button[disabled] {
      opacity: 0.4;
      cursor: default;
    }
    button.icon {
      padding: 4px;
      line-height: 0;
    }
    button.icon svg {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
    button.label {
      font-weight: 500;
      min-width: 9em;
    }
    button.text {
      color: var(--primary-color);
    }
    .content {
      margin-top: 4px;
    }
    .error {
      color: var(--error-color, #db4437);
    }
    .note {
      color: var(--secondary-text-color);
      margin: 4px 0;
    }
    .note.warning {
      color: var(--warning-color, #ffa600);
    }
    .table-wrap {
      /* Scrolls in both axes inside the card so the head rows can stick to its top. */
      overflow: auto;
      max-height: calc(100vh - var(--ecs-sticky-top) - var(--energy-cost-stats-controls-height, 0px) - 8px);
      max-height: calc(100dvh - var(--ecs-sticky-top) - var(--energy-cost-stats-controls-height, 0px) - 8px);
      container-type: inline-size;
    }
    section.comparison {
      margin-top: 12px;
    }
    section.comparison.loading .table-wrap {
      opacity: 0.5;
    }
    section.comparison h3 .loading {
      margin-inline-start: 8px;
      font-size: 0.85rem;
      font-weight: 400;
    }
    section.comparison h3 {
      margin: 0 0 4px;
      font-size: 1rem;
      font-weight: 500;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      font-size: 0.9rem;
    }
    th,
    td {
      padding: 4px 6px;
      white-space: nowrap;
    }
    thead {
      position: sticky;
      top: 0;
      z-index: 2;
    }
    thead th {
      color: var(--secondary-text-color);
      font-weight: 500;
      background: var(--ha-card-background, var(--card-background-color, white));
      /* A shadow, not a border: borders of sticky cells scroll away in collapsed tables. */
      box-shadow: inset 0 -1px 0 var(--divider-color);
    }
    thead tr:first-child th {
      vertical-align: top;
    }
    button.sort {
      display: block;
      width: 100%;
      padding: 0;
      border-radius: 0;
      color: inherit;
      font-weight: inherit;
      text-align: inherit;
      white-space: inherit;
    }
    button.sort:hover:not([disabled]) {
      background: none;
      color: var(--primary-text-color);
    }
    button.sort:focus-visible {
      outline: 2px solid var(--primary-color);
      outline-offset: 2px;
    }
    .sort-indicator {
      margin-inline-start: 4px;
      font-size: 0.75em;
    }
    th.avg {
      text-align: end;
    }
    th.zone {
      text-align: center;
    }
    th.zone .price {
      display: block;
      font-size: 0.8em;
      font-weight: 400;
    }
    .group-start {
      border-inline-start: 1px solid var(--divider-color);
    }
    th.name {
      text-align: start;
      position: sticky;
      left: 0;
      background: var(--card-background-color, var(--ha-card-background, white));
      /* A shadow, not a border: borders of a sticky cell scroll away in collapsed tables. */
      box-shadow: inset -1px 0 0 var(--divider-color);
      z-index: 1;
    }
    thead th.name {
      z-index: 3;
      box-shadow:
        inset -1px 0 0 var(--divider-color),
        inset 0 -1px 0 var(--divider-color);
    }
    tbody th.name,
    tfoot th.name {
      white-space: normal;
      overflow-wrap: anywhere;
      min-width: 6.5em;
      max-width: max(6.5em, 35cqi);
    }
    tr.nested th.name {
      padding-inline-start: calc(6px + var(--depth, 0) * 1.2em);
    }
    .nested-note {
      font-size: 0.85em;
    }
    tbody th.name {
      font-weight: 400;
    }
    .num {
      text-align: end;
      font-variant-numeric: tabular-nums;
    }
    .strong {
      font-weight: 500;
    }
    tbody tr + tr {
      border-top: 1px solid var(--divider-color);
    }
    tfoot tr {
      border-top: 2px solid var(--divider-color);
      font-weight: 600;
    }
    tfoot th.name {
      font-weight: 600;
    }
    .badge {
      display: inline-block;
      margin-inline-start: 4px;
      min-width: 1.2em;
      text-align: center;
      border-radius: 8px;
      font-size: 0.8em;
      cursor: help;
      color: var(--text-primary-color, white);
      background: var(--warning-color, #ffa600);
    }
    .badge.partial,
    .badge.missing {
      background: var(--error-color, #db4437);
    }
    .sub {
      display: block;
      font-size: 0.8em;
      color: var(--secondary-text-color);
    }
    details {
      margin-top: 12px;
    }
    summary {
      cursor: pointer;
      font-weight: 500;
    }
    .issues ul {
      margin: 4px 0;
      padding-inline-start: 20px;
      color: var(--secondary-text-color);
    }
  `}};var Dt="energy-cost-stats-panel",Ke="M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",mt=class extends ${constructor(){super(...arguments);this.narrow=!1;this._cardKey=""}static{this.properties={hass:{attribute:!1,noAccessor:!0},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1},_error:{state:!0}}}get hass(){return this._hass}set hass(e){let r=this._hass;this._hass=e,this._card&&(this._card.hass=e),ct(e,r)&&this.requestUpdate("hass",r)}willUpdate(e){let r={title:"",...this.panel?.config?.card??{},type:`custom:${y}`},n=JSON.stringify(r);if(!(n===this._cardKey&&(this._card||this._error))){this._cardKey=n;try{let i=document.createElement(y);i.setConfig(r),i.hass=this._hass,this._card=i,this._error=void 0}catch(i){this._card=void 0,this._error=i instanceof Error?i.message:String(i)}}}_toggleMenu(){this.dispatchEvent(new Event("hass-toggle-menu",{bubbles:!0,composed:!0}))}render(){let e=new N(this._hass?.locale?.language??this._hass?.language);return h`
      <div class="toolbar">
        ${this.narrow?h`<button class="menu" aria-label=${e.t("menu")} @click=${this._toggleMenu}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d=${Ke}></path></svg>
            </button>`:p}
        <div class="title">${this.panel?.title??""}</div>
      </div>
      <div class="content ${this.narrow?"narrow":""}">
        ${this._error?h`<div class="error" role="alert">${this._error}</div>`:this._card}
      </div>
    `}static{this.styles=L`
    :host {
      display: block;
      min-height: 100vh;
      /* The card's period controls stick directly under the panel bar. */
      --energy-cost-stats-sticky-top: var(--header-height, 56px);
      background: var(--primary-background-color);
      color: var(--primary-text-color);
    }
    .toolbar {
      position: sticky;
      top: 0;
      z-index: 5;
      display: flex;
      align-items: center;
      gap: 8px;
      box-sizing: border-box;
      height: var(--header-height, 56px);
      padding: 0 12px;
      background-color: var(--app-header-background-color, var(--primary-color));
      color: var(--app-header-text-color, var(--text-primary-color, #fff));
      font-size: 20px;
      font-weight: 400;
    }
    .menu {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      padding: 0;
      border: none;
      border-radius: 50%;
      background: none;
      color: inherit;
      cursor: pointer;
    }
    .menu svg {
      width: 24px;
      height: 24px;
      fill: currentColor;
    }
    .title {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .content {
      padding: 16px;
    }
    .content.narrow {
      padding: 8px;
    }
    .error {
      color: var(--error-color);
    }
  `}};var Ve=3e4;function Mt(){let s=window.customElements;s.get(y)||(s.define(y,ht),window.customCards=window.customCards??[],window.customCards.some(t=>t.type===y)||window.customCards.push({type:y,name:"Energy Cost Stats",description:"Electricity cost per device, split by tariff zones",preview:!1})),s.get(Dt)||s.define(Dt,mt)}function Ge(){document.querySelector("home-assistant")!==null&&!window.customElements.get("home-assistant")?(window.customElements.whenDefined("home-assistant").then(Mt),setTimeout(()=>{window.customElements.get(y)||(console.warn(`${y}: the frontend did not boot in time; defining the card anyway`),Mt())},Ve)):Mt()}Ge();export{Ve as BOOT_TIMEOUT_MS,Mt as defineCard,Ge as registerCard};
