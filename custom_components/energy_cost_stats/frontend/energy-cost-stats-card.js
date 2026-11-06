var G=globalThis,j=G.ShadowRoot&&(G.ShadyCSS===void 0||G.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,dt=Symbol(),Et=new WeakMap,L=class{constructor(t,e,r){if(this._$cssResult$=!0,r!==dt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(j&&t===void 0){let r=e!==void 0&&e.length===1;r&&(t=Et.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),r&&Et.set(e,t))}return t}toString(){return this.cssText}},kt=n=>new L(typeof n=="string"?n:n+"",void 0,dt),ct=(n,...t)=>{let e=n.length===1?n[0]:t.reduce((r,i,s)=>r+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+n[s+1],n[0]);return new L(e,n,dt)},St=(n,t)=>{if(j)n.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let r=document.createElement("style"),i=G.litNonce;i!==void 0&&r.setAttribute("nonce",i),r.textContent=e.cssText,n.appendChild(r)}},lt=j?n=>n:n=>n instanceof CSSStyleSheet?(t=>{let e="";for(let r of t.cssRules)e+=r.cssText;return kt(e)})(n):n;var{is:oe,defineProperty:ae,getOwnPropertyDescriptor:de,getOwnPropertyNames:ce,getOwnPropertySymbols:le,getPrototypeOf:ue}=Object,V=globalThis,Ct=V.trustedTypes,he=Ct?Ct.emptyScript:"",pe=V.reactiveElementPolyfillSupport,M=(n,t)=>n,ut={toAttribute(n,t){switch(t){case Boolean:n=n?he:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,t){let e=n;switch(t){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},Pt=(n,t)=>!oe(n,t),Tt={attribute:!0,type:String,converter:ut,reflect:!1,useDefault:!1,hasChanged:Pt};Symbol.metadata??=Symbol("metadata"),V.litPropertyMetadata??=new WeakMap;var y=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Tt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let r=Symbol(),i=this.getPropertyDescriptor(t,r,e);i!==void 0&&ae(this.prototype,t,i)}}static getPropertyDescriptor(t,e,r){let{get:i,set:s}=de(this.prototype,t)??{get(){return this[e]},set(o){this[e]=o}};return{get:i,set(o){let c=i?.call(this);s?.call(this,o),this.requestUpdate(t,c,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Tt}static _$Ei(){if(this.hasOwnProperty(M("elementProperties")))return;let t=ue(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(M("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(M("properties"))){let e=this.properties,r=[...ce(e),...le(e)];for(let i of r)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[r,i]of e)this.elementProperties.set(r,i)}this._$Eh=new Map;for(let[e,r]of this.elementProperties){let i=this._$Eu(e,r);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let r=new Set(t.flat(1/0).reverse());for(let i of r)e.unshift(lt(i))}else t!==void 0&&e.push(lt(t));return e}static _$Eu(t,e){let r=e.attribute;return r===!1?void 0:typeof r=="string"?r:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let r of e.keys())this.hasOwnProperty(r)&&(t.set(r,this[r]),delete this[r]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return St(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,r){this._$AK(t,r)}_$ET(t,e){let r=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,r);if(i!==void 0&&r.reflect===!0){let s=(r.converter?.toAttribute!==void 0?r.converter:ut).toAttribute(e,r.type);this._$Em=t,s==null?this.removeAttribute(i):this.setAttribute(i,s),this._$Em=null}}_$AK(t,e){let r=this.constructor,i=r._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let s=r.getPropertyOptions(i),o=typeof s.converter=="function"?{fromAttribute:s.converter}:s.converter?.fromAttribute!==void 0?s.converter:ut;this._$Em=i;let c=o.fromAttribute(e,s.type);this[i]=c??this._$Ej?.get(i)??c,this._$Em=null}}requestUpdate(t,e,r,i=!1,s){if(t!==void 0){let o=this.constructor;if(i===!1&&(s=this[t]),r??=o.getPropertyOptions(t),!((r.hasChanged??Pt)(s,e)||r.useDefault&&r.reflect&&s===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,r))))return;this.C(t,e,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:r,reflect:i,wrapped:s},o){r&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),s!==!0||o!==void 0)||(this._$AL.has(t)||(this.hasUpdated||r||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,s]of this._$Ep)this[i]=s;this._$Ep=void 0}let r=this.constructor.elementProperties;if(r.size>0)for(let[i,s]of r){let{wrapped:o}=s,c=this[i];o!==!0||this._$AL.has(i)||c===void 0||this.C(i,void 0,s,c)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(e)):this._$EM()}catch(r){throw t=!1,this._$EM(),r}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};y.elementStyles=[],y.shadowRootOptions={mode:"open"},y[M("elementProperties")]=new Map,y[M("finalized")]=new Map,pe?.({ReactiveElement:y}),(V.reactiveElementVersions??=[]).push("2.1.2");var pt=globalThis,Rt=n=>n,K=pt.trustedTypes,Dt=K?K.createPolicy("lit-html",{createHTML:n=>n}):void 0,gt="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,mt="?"+$,ge=`<${mt}>`,S=document,O=()=>S.createComment(""),H=n=>n===null||typeof n!="object"&&typeof n!="function",_t=Array.isArray,Ht=n=>_t(n)||typeof n?.[Symbol.iterator]=="function",ht=`[ 	
\f\r]`,N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ut=/-->/g,Lt=/>/g,E=RegExp(`>|${ht}(?:([^\\s"'>=/]+)(${ht}*=${ht}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Mt=/'/g,Nt=/"/g,It=/^(?:script|style|textarea|title)$/i,ft=n=>(t,...e)=>({_$litType$:n,strings:t,values:e}),u=ft(1),Ne=ft(2),Oe=ft(3),m=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),Ot=new WeakMap,k=S.createTreeWalker(S,129);function Bt(n,t){if(!_t(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return Dt!==void 0?Dt.createHTML(t):t}var zt=(n,t)=>{let e=n.length-1,r=[],i,s=t===2?"<svg>":t===3?"<math>":"",o=N;for(let c=0;c<e;c++){let a=n[c],d,h,p=-1,f=0;for(;f<a.length&&(o.lastIndex=f,h=o.exec(a),h!==null);)f=o.lastIndex,o===N?h[1]==="!--"?o=Ut:h[1]!==void 0?o=Lt:h[2]!==void 0?(It.test(h[2])&&(i=RegExp("</"+h[2],"g")),o=E):h[3]!==void 0&&(o=E):o===E?h[0]===">"?(o=i??N,p=-1):h[1]===void 0?p=-2:(p=o.lastIndex-h[2].length,d=h[1],o=h[3]===void 0?E:h[3]==='"'?Nt:Mt):o===Nt||o===Mt?o=E:o===Ut||o===Lt?o=N:(o=E,i=void 0);let b=o===E&&n[c+1].startsWith("/>")?" ":"";s+=o===N?a+ge:p>=0?(r.push(d),a.slice(0,p)+gt+a.slice(p)+$+b):a+$+(p===-2?c:b)}return[Bt(n,s+(n[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),r]},I=class n{constructor({strings:t,_$litType$:e},r){let i;this.parts=[];let s=0,o=0,c=t.length-1,a=this.parts,[d,h]=zt(t,e);if(this.el=n.createElement(d,r),k.currentNode=this.el.content,e===2||e===3){let p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(i=k.nextNode())!==null&&a.length<c;){if(i.nodeType===1){if(i.hasAttributes())for(let p of i.getAttributeNames())if(p.endsWith(gt)){let f=h[o++],b=i.getAttribute(p).split($),F=/([.?@])?(.*)/.exec(f);a.push({type:1,index:s,name:F[2],strings:b,ctor:F[1]==="."?Z:F[1]==="?"?W:F[1]==="@"?Q:T}),i.removeAttribute(p)}else p.startsWith($)&&(a.push({type:6,index:s}),i.removeAttribute(p));if(It.test(i.tagName)){let p=i.textContent.split($),f=p.length-1;if(f>0){i.textContent=K?K.emptyScript:"";for(let b=0;b<f;b++)i.append(p[b],O()),k.nextNode(),a.push({type:2,index:++s});i.append(p[f],O())}}}else if(i.nodeType===8)if(i.data===mt)a.push({type:2,index:s});else{let p=-1;for(;(p=i.data.indexOf($,p+1))!==-1;)a.push({type:7,index:s}),p+=$.length-1}s++}}static createElement(t,e){let r=S.createElement("template");return r.innerHTML=t,r}};function C(n,t,e=n,r){if(t===m)return t;let i=r!==void 0?e._$Co?.[r]:e._$Cl,s=H(t)?void 0:t._$litDirective$;return i?.constructor!==s&&(i?._$AO?.(!1),s===void 0?i=void 0:(i=new s(n),i._$AT(n,e,r)),r!==void 0?(e._$Co??=[])[r]=i:e._$Cl=i),i!==void 0&&(t=C(n,i._$AS(n,t.values),i,r)),t}var Y=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:r}=this._$AD,i=(t?.creationScope??S).importNode(e,!0);k.currentNode=i;let s=k.nextNode(),o=0,c=0,a=r[0];for(;a!==void 0;){if(o===a.index){let d;a.type===2?d=new D(s,s.nextSibling,this,t):a.type===1?d=new a.ctor(s,a.name,a.strings,this,t):a.type===6&&(d=new X(s,this,t)),this._$AV.push(d),a=r[++c]}o!==a?.index&&(s=k.nextNode(),o++)}return k.currentNode=S,i}p(t){let e=0;for(let r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(t,r,e),e+=r.strings.length-2):r._$AI(t[e])),e++}},D=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,r,i){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=r,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=C(this,t,e),H(t)?t===l||t==null||t===""?(this._$AH!==l&&this._$AR(),this._$AH=l):t!==this._$AH&&t!==m&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Ht(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==l&&H(this._$AH)?this._$AA.nextSibling.data=t:this.T(S.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:r}=t,i=typeof r=="number"?this._$AC(t):(r.el===void 0&&(r.el=I.createElement(Bt(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===i)this._$AH.p(e);else{let s=new Y(i,this),o=s.u(this.options);s.p(e),this.T(o),this._$AH=s}}_$AC(t){let e=Ot.get(t.strings);return e===void 0&&Ot.set(t.strings,e=new I(t)),e}k(t){_t(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,r,i=0;for(let s of t)i===e.length?e.push(r=new n(this.O(O()),this.O(O()),this,this.options)):r=e[i],r._$AI(s),i++;i<e.length&&(this._$AR(r&&r._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let r=Rt(t).nextSibling;Rt(t).remove(),t=r}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},T=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,r,i,s){this.type=1,this._$AH=l,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=s,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=l}_$AI(t,e=this,r,i){let s=this.strings,o=!1;if(s===void 0)t=C(this,t,e,0),o=!H(t)||t!==this._$AH&&t!==m,o&&(this._$AH=t);else{let c=t,a,d;for(t=s[0],a=0;a<s.length-1;a++)d=C(this,c[r+a],e,a),d===m&&(d=this._$AH[a]),o||=!H(d)||d!==this._$AH[a],d===l?t=l:t!==l&&(t+=(d??"")+s[a+1]),this._$AH[a]=d}o&&!i&&this.j(t)}j(t){t===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Z=class extends T{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===l?void 0:t}},W=class extends T{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==l)}},Q=class extends T{constructor(t,e,r,i,s){super(t,e,r,i,s),this.type=5}_$AI(t,e=this){if((t=C(this,t,e,0)??l)===m)return;let r=this._$AH,i=t===l&&r!==l||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,s=t!==l&&(r===l||i);i&&this.element.removeEventListener(this.name,this,r),s&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},X=class{constructor(t,e,r){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(t){C(this,t)}},qt={M:gt,P:$,A:mt,C:1,L:zt,R:Y,D:Ht,V:C,I:D,H:T,N:W,U:Q,B:Z,F:X},me=pt.litHtmlPolyfillSupport;me?.(I,D),(pt.litHtmlVersions??=[]).push("3.3.3");var Ft=(n,t,e)=>{let r=e?.renderBefore??t,i=r._$litPart$;if(i===void 0){let s=e?.renderBefore??null;r._$litPart$=i=new D(t.insertBefore(O(),s),s,void 0,e??{})}return i._$AI(n),i};var yt=globalThis,w=class extends y{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Ft(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return m}};w._$litElement$=!0,w.finalized=!0,yt.litElementHydrateSupport?.({LitElement:w});var _e=yt.litElementPolyfillSupport;_e?.({LitElement:w});(yt.litElementVersions??=[]).push("4.2.2");var P={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Gt=n=>(...t)=>({_$litDirective$:n,values:t}),J=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,r){this._$Ct=t,this._$AM=e,this._$Ci=r}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var{I:Xe}=qt;var jt=n=>n.strings===void 0;var fe={},Vt=(n,t=fe)=>n._$AH=t;var tt=Gt(class extends J{constructor(n){if(super(n),n.type!==P.PROPERTY&&n.type!==P.ATTRIBUTE&&n.type!==P.BOOLEAN_ATTRIBUTE)throw Error("The `live` directive is not allowed on child or event bindings");if(!jt(n))throw Error("`live` bindings can only contain a single expression")}render(n){return n}update(n,[t]){if(t===m||t===l)return t;let e=n.element,r=n.name;if(n.type===P.PROPERTY){if(t===e[r])return m}else if(n.type===P.BOOLEAN_ATTRIBUTE){if(!!t===e.hasAttribute(r))return m}else if(n.type===P.ATTRIBUTE&&e.getAttribute(r)===t+"")return m;return Vt(n),t}});var z=["today","yesterday","this_week","last_week","this_month","last_month","this_quarter","this_year","now-7d","now-30d","now-12m"];function _(n){let t=/^(\d{4})-(\d{2})-(\d{2})$/.exec(n);if(!t)throw new Error(`invalid date: ${n}`);let[,e,r,i]=t;return new Date(Date.UTC(Number(e),Number(r)-1,Number(i)))}function et(n){return n.toISOString().slice(0,10)}function vt(n){try{return et(_(n))===n}catch{return!1}}function g(n,t){return et(new Date(_(n).getTime()+t*864e5))}function U(n,t=0){let e=_(n);return et(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t,1)))}function R(n,t=0){let e=_(n);return et(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t+1,0)))}function $t(n){let t=(_(n).getUTCDay()+6)%7;return g(n,-t)}function q(n){return Math.round((_(n.end).getTime()-_(n.start).getTime())/864e5)+1}function bt(n){let t=_(n.start);if(t.getUTCDate()!==1||R(n.end)!==n.end)return null;let e=_(n.end);return(e.getUTCFullYear()-t.getUTCFullYear())*12+(e.getUTCMonth()-t.getUTCMonth())+1}function A(n,t=new Date){let e={year:"numeric",month:"2-digit",day:"2-digit"},r;try{r=new Intl.DateTimeFormat("en-CA",{...e,timeZone:n}).formatToParts(t)}catch{r=new Intl.DateTimeFormat("en-CA",e).formatToParts(t)}let i=s=>r.find(o=>o.type===s)?.value??"";return`${i("year")}-${i("month")}-${i("day")}`}function v(n,t){switch(n){case"today":return{start:t,end:t};case"yesterday":{let e=g(t,-1);return{start:e,end:e}}case"this_week":{let e=$t(t);return{start:e,end:g(e,6)}}case"last_week":{let e=g($t(t),-7);return{start:e,end:g(e,6)}}case"this_month":return{start:U(t),end:R(t)};case"last_month":return{start:U(t,-1),end:R(t,-1)};case"this_quarter":{let e=_(t).getUTCMonth(),r=U(t,-(e%3));return{start:r,end:R(r,2)}}case"this_year":{let e=t.slice(0,4);return{start:`${e}-01-01`,end:`${e}-12-31`}}case"now-7d":return{start:g(t,-6),end:t};case"now-30d":return{start:g(t,-29),end:t};case"now-12m":return{start:U(t,-11),end:R(t)}}}function wt(n){let t=bt(n);if(t!==null){let r=_(n.start).getUTCMonth();return t===1?"month":t===3&&r%3===0?"quarter":t===12&&r===0?"year":"months"}let e=q(n);return e===1?"day":e===7&&$t(n.start)===n.start?"week":"days"}function At(n,t){let e=bt(n);if(e!==null){let i=e*t;return{start:U(n.start,i),end:R(n.end,i)}}let r=q(n)*t;return{start:g(n.start,r),end:g(n.end,r)}}function Kt(n,t){switch(wt(n)){case"day":return v("today",t);case"week":return v("this_week",t);case"month":return v("this_month",t);case"quarter":return v("this_quarter",t);case"year":return v("this_year",t);case"months":{let r=bt(n)??1;return{start:U(t,-(r-1)),end:R(t)}}case"days":return{start:g(t,-(q(n)-1)),end:t}}}function rt(n,t){return n.start<=t&&t<=n.end}function B(n){return g(n.end,1)}function nt(n,t,e=new Date){let r=A(t,e);if(!rt(n,r))return B(n);let i;try{i=new Intl.DateTimeFormat("en-GB",{timeZone:t,hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(e)}catch{return B(n)}let s=Number(i.find(d=>d.type==="hour")?.value),o=Number(i.find(d=>d.type==="minute")?.value);if(!Number.isFinite(s)||o!==e.getUTCMinutes())return B(n);let c=n.start===r?Math.max(s,1):s,a=ye(t,e,c-s);return`${r}T${String(c).padStart(2,"0")}:00:00${a}`}function ye(n,t,e){let r=new Date(t.getTime()+e*36e5),i=new Intl.DateTimeFormat("en-US",{timeZone:n,timeZoneName:"longOffset"}).formatToParts(r).find(o=>o.type==="timeZoneName")?.value??"GMT",s=/^GMT([+-]\d{2}):?(\d{2})?$/.exec(i);return s?`${s[1]}:${s[2]??"00"}`:"+00:00"}var $e=31;function Yt(n){let t=q(n);return t<=2?"hour":t<=45?"day":t<=120?"week":"month"}function it(n,t){return n!=="hour"||q(t)<=$e}var Zt="energy_";function ve(n,t){return n?[`_${n}`]:t?[`_${Zt}${t}`]:[]}function Wt(n){return n.startsWith(Zt)}function Qt(n,t){return n||t.split("/").filter(Boolean)[0]}function be(n){if(!n||typeof n!="object")return!1;let t=n;return t.start instanceof Date&&typeof t.subscribe=="function"}function Xt(n,t,e){if(!(!n||typeof n!="object"))for(let r of ve(t,e)){let i=n[r];if(be(i))return i}}function Jt(n,t){return n?.time_zone==="server"?t:void 0}function te(n,t){if(!(n.start instanceof Date)||Number.isNaN(n.start.getTime()))return;let e=A(t,n.start),r=n.end instanceof Date&&!Number.isNaN(n.end.getTime())?A(t,n.end):A(t);return r<e?void 0:{start:e,end:r}}var we={title:"Energy cost",previous:"Previous",next:"Next",now:"Now",refresh:"Refresh",period:"Period",custom:"Custom period",from:"From",to:"To",apply:"Apply",grouping:"Grouping","grouping.auto":"Auto","grouping.hour":"Hours","grouping.day":"Days","grouping.week":"Weeks","grouping.month":"Months","grouping.hour_too_long":"Hours: up to 31 days","preset.today":"Today","preset.yesterday":"Yesterday","preset.this_week":"This week","preset.last_week":"Last week","preset.this_month":"This month","preset.last_month":"Last month","preset.this_quarter":"This quarter","preset.this_year":"This year","preset.now-7d":"Last 7 days","preset.now-30d":"Last 30 days","preset.now-12m":"Last 12 months",device:"Device",total:"Total",kwh:"kWh",cost:"Cost",avg_price:"Avg. price",breakdown:"By period",breakdown_device:"Show",all_devices:"All devices",data_quality:"Data quality",loading:"Loading…",no_devices:"No energy sensors selected. Add them in the integration options.",no_plan:"No tariff plan covers this period: costs are unknown.",unpriced:"{hours} h before the first tariff plan are not priced.","status.complete":"Complete","status.estimated":"Contains estimated hours (spread over a data gap)","status.partial":"Some hours are missing","status.missing":"No data","issue.estimated":"estimated","issue.excluded_negative":"excluded (negative)","issue.excluded_spike":"excluded (spike)","statistics.no_statistics":"no statistics yet","statistics.unsupported":"unsupported sensor","error.not_loaded":"Energy Cost Stats is not set up or not loaded.","error.invalid_period":"Invalid period.","error.period_too_long":"The period is too long for this grouping.","error.unknown_entity":"The card lists a sensor that is not selected in the integration.","error.unknown_command":"The integration is not loaded (restart Home Assistant after installing).","error.generic":"Could not load the report: {message}",coverage:"{measured} measured, {estimated} estimated, {excluded} excluded, {missing} missing of {expected} h",energy_picker_followed:"Period from the Energy date picker on this dashboard",energy_picker_missing:'No Energy date picker on this dashboard: add the "Energy date selection" card or set period_source: card.'},Ae={title:"Стоимость электроэнергии",previous:"Назад",next:"Вперёд",now:"Сейчас",refresh:"Обновить",period:"Период",custom:"Свой период",from:"С",to:"По",apply:"Применить",grouping:"Группировка","grouping.auto":"Авто","grouping.hour":"По часам","grouping.day":"По дням","grouping.week":"По неделям","grouping.month":"По месяцам","grouping.hour_too_long":"По часам: до 31 дня","preset.today":"Сегодня","preset.yesterday":"Вчера","preset.this_week":"Эта неделя","preset.last_week":"Прошлая неделя","preset.this_month":"Этот месяц","preset.last_month":"Прошлый месяц","preset.this_quarter":"Этот квартал","preset.this_year":"Этот год","preset.now-7d":"Последние 7 дней","preset.now-30d":"Последние 30 дней","preset.now-12m":"Последние 12 месяцев",device:"Устройство",total:"Итого",kwh:"кВт·ч",cost:"Сумма",avg_price:"Ср. цена",breakdown:"По периодам",breakdown_device:"Показать",all_devices:"Все устройства",data_quality:"Качество данных",loading:"Загрузка…",no_devices:"Не выбраны датчики энергии. Добавьте их в настройках интеграции.",no_plan:"Для этого периода нет тарифного плана: стоимость неизвестна.",unpriced:"{hours} ч до первого тарифного плана не оценены.","status.complete":"Полные данные","status.estimated":"Есть оценочные часы (распределены по пропуску)","status.partial":"Часть часов отсутствует","status.missing":"Нет данных","issue.estimated":"оценка","issue.excluded_negative":"исключено (отрицательное)","issue.excluded_spike":"исключено (выброс)","statistics.no_statistics":"статистики пока нет","statistics.unsupported":"датчик не поддерживается","error.not_loaded":"Energy Cost Stats не настроена или не загружена.","error.invalid_period":"Неверный период.","error.period_too_long":"Период слишком длинный для этой группировки.","error.unknown_entity":"В карточке указан датчик, не выбранный в интеграции.","error.unknown_command":"Интеграция не загружена (перезапустите Home Assistant после установки).","error.generic":"Не удалось загрузить отчёт: {message}",coverage:"{measured} измерено, {estimated} оценено, {excluded} исключено, {missing} нет из {expected} ч",energy_picker_followed:"Период из выбора периода «Энергия» на этом дашборде",energy_picker_missing:"На дашборде нет выбора периода «Энергия»: добавьте карточку «Выбор даты энергии» или укажите period_source: card."},st=class{constructor(t){this.locale=t||"en",this.table=this.locale.toLowerCase().startsWith("ru")?Ae:we}t(t,e={}){return this.table[t].replace(/\{(\w+)\}/g,(r,i)=>i in e?String(e[i]):`{${i}}`)}preset(t){return this.t(`preset.${t}`)}grouping(t){return this.t(`grouping.${t}`)}number(t,e){return t==null?"—":new Intl.NumberFormat(this.locale,{minimumFractionDigits:e,maximumFractionDigits:e}).format(Number(t))}money(t,e){if(t==null)return"—";if(e)try{return new Intl.NumberFormat(this.locale,{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(t))}catch{}return this.number(t,2)}avgPrice(t,e){return t===null||e===null||Number(e)===0?"—":this.number(String(Number(t)/Number(e)),2)}date(t,e){return new Intl.DateTimeFormat(this.locale,{...e,timeZone:"UTC"}).format(new Date(`${t}T00:00:00Z`))}periodLabel(t){switch(wt(t)){case"day":return this.date(t.start,{day:"numeric",month:"long",year:"numeric"});case"month":return this.date(t.start,{month:"long",year:"numeric"});case"quarter":return`Q${Math.floor(Number(t.start.slice(5,7))/3)+1} ${t.start.slice(0,4)}`;case"year":return t.start.slice(0,4);case"months":return`${this.date(t.start,{month:"short",year:"numeric"})} – ${this.date(t.end,{month:"short",year:"numeric"})}`;default:{let r=t.start.slice(0,4)===t.end.slice(0,4),i=this.date(t.start,{day:"numeric",month:"short",...r?{}:{year:"numeric"}}),s=this.date(t.end,{day:"numeric",month:"short",year:"numeric"});return`${i} – ${s}`}}}bucketLabel(t,e){let r=t.slice(0,10);switch(e){case"hour":return`${this.date(r,{day:"numeric",month:"short"})} ${t.slice(11,16)}`;case"day":return this.date(r,{weekday:"short",day:"numeric",month:"short"});case"week":return this.date(r,{day:"numeric",month:"short",year:"numeric"});case"month":return this.date(r,{month:"long",year:"numeric"});default:return this.t("total")}}};var xe="energy_cost_stats/report";function Ee(n){let t={type:xe,start:n.period.start,end:nt(n.period,n.timeZone,n.now),grouping:n.grouping};return n.entities&&n.entities.length>0&&(t.entities=n.entities),t}function ee(n,t){return n.callWS(Ee(t))}function re(n){if(n&&typeof n=="object"&&"code"in n){let t=n.code;return typeof t=="string"?t:void 0}}function ne(n){return n&&typeof n=="object"&&"message"in n?String(n.message):String(n)}var x="energy-cost-stats-card",ie=["auto","hour","day","week","month"],ke=["card","energy"],Se=600*1e3,Ce="M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",Te="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",se="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";function ot(n){return u`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${n}></path></svg>`}var at=class extends w{constructor(){super(...arguments);this._groupingChoice="auto";this._loading=!1;this._customOpen=!1;this._customStart="";this._customEnd="";this._breakdownEntity="";this._requestSeq=0;this._lastRequestOpen=!1}static{this.properties={hass:{attribute:!1},_config:{state:!0},_period:{state:!0},_groupingChoice:{state:!0},_report:{state:!0},_error:{state:!0},_loading:{state:!0},_customOpen:{state:!0},_customStart:{state:!0},_customEnd:{state:!0},_breakdownEntity:{state:!0}}}static getStubConfig(){return{type:`custom:${x}`,period:"this_month"}}setConfig(e){if(!e||typeof e!="object")throw new Error("Invalid configuration");if(e.period!==void 0&&!z.includes(e.period))throw new Error(`Unknown period: ${String(e.period)}`);if(e.grouping!==void 0&&!ie.includes(e.grouping))throw new Error(`Unknown grouping: ${String(e.grouping)}`);if(e.entities!==void 0&&(!Array.isArray(e.entities)||e.entities.some(i=>typeof i!="string")))throw new Error("entities must be a list of entity ids");if(e.period_source!==void 0&&!ke.includes(e.period_source))throw new Error(`Unknown period_source: ${String(e.period_source)}`);if(e.collection_key!==void 0&&(typeof e.collection_key!="string"||!Wt(e.collection_key)))throw new Error('collection_key must start with "energy_" (as in the energy date picker)');let r=this._config;r&&(this._detachEnergy(),this._energyBroken=void 0),this._config=e,this._groupingChoice=e.grouping??"auto",r&&this._period&&(this._period=void 0,this._report=void 0)}getCardSize(){return 3+(this._report?.devices.length??2)}get _strings(){return new st(this.hass?.locale?.language??this.hass?.language)}get _timeZone(){return this._reportTimeZone??this.hass?.config?.time_zone}_today(){return A(this._timeZone)}get grouping(){let e=this._period;if(!e)return"day";let r=this._groupingChoice;return r!=="auto"&&it(r,e)?r:Yt(e)}connectedCallback(){super.connectedCallback(),this._timer=setInterval(()=>{this._period&&this._lastRequestOpen&&!this._loading&&this._load()},Se)}disconnectedCallback(){super.disconnectedCallback(),this._timer!==void 0&&clearInterval(this._timer),this._timer=void 0,this._detachEnergy()}willUpdate(e){this.hass&&this._config&&this.isConnected&&!this._energy&&this._attachEnergy(),this.hass&&this._config&&!this._period&&(this._period=v(this._config.period??"this_month",this._today())),super.willUpdate(e)}get followsEnergyPicker(){return this._energy!==void 0}_attachEnergy(){if(this._config?.period_source!=="energy")return;let e=Xt(this.hass?.connection,this._config.collection_key,Qt(this.hass?.panelUrl,window.location.pathname));if(!e||e===this._energyBroken)return;this._energy=e;let r=i=>{let s=te(i,Jt(this.hass?.locale,this.hass?.config?.time_zone));s&&(s.start!==this._period?.start||s.end!==this._period?.end)&&(this._customOpen=!1,this._period=s)};r(e);try{this._unsubEnergy=e.subscribe(r)}catch{this._energy=void 0,this._energyBroken=e}}_detachEnergy(){try{this._unsubEnergy?.()}catch{}this._unsubEnergy=void 0,this._energy=void 0}updated(e){super.updated(e),!(!this.hass||!this._period)&&(e.has("_period")||e.has("_groupingChoice")||e.has("hass")&&e.get("hass")===void 0)&&this._load()}async _load(){let e=this.hass,r=this._period;if(!e||!r)return;let i=++this._requestSeq,s=this._timeZone;this._loading=!0;try{let o=await ee(e,{period:r,grouping:this.grouping,entities:this._config?.entities,timeZone:s});if(i!==this._requestSeq)return;this._report=o,this._error=void 0,this._reportTimeZone=o.time_zone,this._lastRequestOpen=nt(r,o.time_zone)!==B(r),o.time_zone!==s&&rt(r,A(o.time_zone))&&this._load()}catch(o){if(i!==this._requestSeq)return;let c=re(o),d=c?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_command:"error.unknown_command"}[c]:void 0;this._error=d?this._strings.t(d):this._strings.t("error.generic",{message:ne(o)}),this._report=void 0}finally{i===this._requestSeq&&(this._loading=!1)}}_selectedPreset(){if(!this._period)return"";let e=this._today(),r=this._period;return z.find(i=>{let s=v(i,e);return s.start===r.start&&s.end===r.end})??""}_onPreset(e){let r=e.target.value;if(r==="custom"){this._openCustom();return}z.includes(r)&&(this._customOpen=!1,this._period=v(r,this._today()))}_openCustom(){this._customOpen=!0,this._customStart=this._period?.start??this._today(),this._customEnd=this._period?.end??this._today()}_applyCustom(){let e=this._customStart,r=this._customEnd;!vt(e)||!vt(r)||(this._period=e<=r?{start:e,end:r}:{start:r,end:e},this._customOpen=!1)}_shift(e){this._period&&(this._period=At(this._period,e))}_now(){this._period&&(this._period=Kt(this._period,this._today()))}_onGrouping(e){this._groupingChoice=e.target.value}render(){if(!this._config||!this.hass||!this._period)return l;let e=this._strings,r=this._config.title??e.t("title");return u`
      <ha-card>
        <div class="header">
          <div class="title">${r}</div>
          ${this._loading?u`<div class="loading" role="status">${e.t("loading")}</div>`:l}
        </div>
        ${this._energy?this._renderFollowedPeriod(e):u`${this._config.period_source==="energy"?u`<div class="note warning">${e.t("energy_picker_missing")}</div>`:l}${this._renderPicker(e)}`}
        <div class="content">
          ${this._error?u`<div class="error" role="alert">${this._error}</div>`:this._report?this._renderReport(e,this._report):l}
        </div>
      </ha-card>
    `}_renderFollowedPeriod(e){return u`
      <div class="picker followed">
        <span class="label" title=${e.t("energy_picker_followed")}>
          ${e.periodLabel(this._period)}
        </span>
        <button
          class="icon refresh"
          title=${e.t("refresh")}
          aria-label=${e.t("refresh")}
          @click=${()=>{this._load()}}
        >
          ${ot(se)}
        </button>
      </div>
    `}_renderPicker(e){let r=this._period,i=this._selectedPreset(),s=this._today(),o=rt(r,s),c=At(r,1).start>s;return u`
      <div class="picker">
        <select
          class="preset"
          aria-label=${e.t("period")}
          .value=${tt(i)}
          @change=${this._onPreset}
        >
          <option value="" ?hidden=${i!==""} ?selected=${i===""}>
            ${e.t("custom")}
          </option>
          ${z.map(a=>u`<option value=${a} ?selected=${a===i}>${e.preset(a)}</option>`)}
          <option value="custom">${e.t("custom")}…</option>
        </select>
        <div class="nav">
          <button
            class="icon prev"
            title=${e.t("previous")}
            aria-label=${e.t("previous")}
            @click=${()=>this._shift(-1)}
          >
            ${ot(Ce)}
          </button>
          <button class="label" title=${e.t("custom")} @click=${this._openCustom}>
            ${e.periodLabel(r)}
          </button>
          <button
            class="icon next"
            title=${e.t("next")}
            aria-label=${e.t("next")}
            ?disabled=${c}
            @click=${()=>this._shift(1)}
          >
            ${ot(Te)}
          </button>
          <button class="text now" ?disabled=${o} @click=${this._now}>
            ${e.t("now")}
          </button>
        </div>
        <button
          class="icon refresh"
          title=${e.t("refresh")}
          aria-label=${e.t("refresh")}
          @click=${()=>{this._load()}}
        >
          ${ot(se)}
        </button>
      </div>
      ${this._customOpen?u`<div class="custom">
            <label
              >${e.t("from")}
              <input
                type="date"
                class="custom-start"
                .value=${this._customStart}
                max=${s}
                @change=${a=>{this._customStart=a.target.value}}
            /></label>
            <label
              >${e.t("to")}
              <input
                type="date"
                class="custom-end"
                .value=${this._customEnd}
                @change=${a=>{this._customEnd=a.target.value}}
            /></label>
            <button class="text apply" @click=${this._applyCustom}>${e.t("apply")}</button>
          </div>`:l}
    `}_renderReport(e,r){if(r.devices.length===0)return u`<div class="note">${e.t("no_devices")}</div>`;let i=new Map(r.devices.map(c=>[c.entity_id,c])),s=r.totals,o=r.plans.length===0;return u`
      ${o?u`<div class="note warning">${e.t("no_plan")}</div>`:l}
      ${!o&&r.unpriced_hours>0?u`<div class="note warning">
            ${e.t("unpriced",{hours:r.unpriced_hours})}
          </div>`:l}
      <div class="table-wrap">
        <table class="devices">
          ${this._renderHead(e,r,e.t("device"),s)}
          <tbody>
            ${s.rows.map(c=>{let a=c.entity_id?i.get(c.entity_id):void 0,d=a?.name??c.entity_id??"",h=a&&a.statistics!=="ok"?e.t(`statistics.${a.statistics}`):"";return this._renderRow(e,r,c,d,h)})}
          </tbody>
          <tfoot>
            ${this._renderRow(e,r,s.total,e.t("total"),"")}
          </tfoot>
        </table>
      </div>
      ${r.grouping!=="total"?this._renderBreakdown(e,r):l}
      ${r.issues.length>0?this._renderIssues(e,r,i):l}
    `}_renderHead(e,r,i,s){let o=r.currency;return u`
      <thead>
        <tr>
          <th rowspan="2" class="name">${i}</th>
          ${r.zones.map((c,a)=>{let d=s.total.zones[a]?.price??null;return u`<th colspan="2" class="zone">
              ${c.name}${d!==null?u`<span class="price">${e.money(d,o)}</span>`:l}
            </th>`})}
          <th colspan="3" class="zone sum">${e.t("total")}</th>
        </tr>
        <tr>
          ${r.zones.map(()=>u`<th class="num">${e.t("kwh")}</th><th class="num">${e.t("cost")}</th>`)}
          <th class="num">${e.t("kwh")}</th>
          <th class="num">${e.t("cost")}</th>
          <th class="num">${e.t("avg_price")}</th>
        </tr>
      </thead>
    `}_renderRow(e,r,i,s,o){let c=r.currency,a=i.coverage,d=e.t("coverage",{measured:a.measured,estimated:a.estimated,excluded:a.excluded,missing:a.missing,expected:a.expected});return u`
      <tr class="status-${i.status}">
        <th scope="row" class="name">
          <span>${s}</span>
          ${i.status!=="complete"?u`<span
                class="badge ${i.status}"
                title="${e.t(`status.${i.status}`)} · ${d}"
                >${i.status==="estimated"?"≈":"!"}</span
              >`:l}
          ${o?u`<span class="sub">${o}</span>`:l}
        </th>
        ${i.zones.map(h=>u`<td class="num">${e.number(h.kwh,2)}</td>
              <td class="num">${e.money(h.cost,c)}</td>`)}
        <td class="num strong">${e.number(i.kwh,2)}</td>
        <td class="num strong">${e.money(i.cost,c)}</td>
        <td class="num">${e.avgPrice(i.cost,i.kwh)}</td>
      </tr>
    `}_renderBreakdown(e,r){let i=this._breakdownEntity,s=i?r.devices.findIndex(d=>d.entity_id===i):-1,o=d=>(s>=0?d.rows.find(h=>h.entity_id===i):void 0)??d.total,c=this._groupingChoice,a=c==="auto"||it(c,this._period)?c:"auto";return u`
      <details class="breakdown" ?open=${this._config?.show_breakdown??!1}>
        <summary>${e.t("breakdown")}</summary>
        <div class="breakdown-controls">
          <label
            >${e.t("breakdown_device")}
            <select
              class="breakdown-device"
              .value=${tt(s>=0?i:"")}
              @change=${d=>{this._breakdownEntity=d.target.value}}
            >
              <option value="">${e.t("all_devices")}</option>
              ${r.devices.map(d=>u`<option value=${d.entity_id} ?selected=${d.entity_id===i}>
                    ${d.name}
                  </option>`)}
            </select>
          </label>
          <label
            >${e.t("grouping")}
            <select class="grouping" .value=${tt(a)} @change=${this._onGrouping}>
              ${ie.map(d=>{let h=d==="auto"||it(d,this._period);return u`<option
                  value=${d}
                  ?disabled=${!h}
                  ?selected=${d===a}
                >
                  ${h?e.grouping(d):e.t("grouping.hour_too_long")}
                </option>`})}
            </select>
          </label>
        </div>
        <div class="table-wrap">
          <table class="buckets">
            ${this._renderHead(e,r,e.t("period"),r.totals)}
            <tbody>
              ${r.buckets.map(d=>this._renderRow(e,r,o(d),this._bucketLabel(e,r,d),""))}
            </tbody>
            <tfoot>
              ${this._renderRow(e,r,o(r.totals),e.t("total"),"")}
            </tfoot>
          </table>
        </div>
      </details>
    `}_bucketLabel(e,r,i){if(r.grouping==="week"){let s=i.start.slice(0,10);return e.periodLabel({start:s,end:g(s,6)})}return e.bucketLabel(i.start,r.grouping)}_renderIssues(e,r,i){return u`
      <details class="issues">
        <summary>${e.t("data_quality")} (${r.issues.length})</summary>
        <ul>
          ${r.issues.map(s=>u`<li>
                <span class="who">${i.get(s.entity_id)?.name??s.entity_id}</span>:
                ${e.t(`issue.${s.kind}`)},
                ${e.bucketLabel(s.start,"hour")} – ${e.bucketLabel(s.end,"hour")}
                (${s.hours} h, ${e.number(s.kwh,3)} ${e.t("kwh")})
              </li>`)}
        </ul>
      </details>
    `}static{this.styles=ct`
    :host {
      display: block;
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
    .picker,
    .custom,
    .breakdown-controls {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin: 4px 0 8px;
    }
    .picker.followed {
      justify-content: space-between;
    }
    .picker.followed .label {
      font-weight: 500;
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
      overflow-x: auto;
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
    thead th {
      color: var(--secondary-text-color);
      font-weight: 500;
      border-bottom: 1px solid var(--divider-color);
    }
    th.zone {
      text-align: center;
    }
    th.zone .price {
      display: block;
      font-size: 0.8em;
      font-weight: 400;
    }
    th.name {
      text-align: start;
      position: sticky;
      left: 0;
      background: var(--card-background-color, var(--ha-card-background, white));
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
  `}};var Pe=3e4;function xt(){let n=window.customElements;n.get(x)||(n.define(x,at),window.customCards=window.customCards??[],window.customCards.some(t=>t.type===x)||window.customCards.push({type:x,name:"Energy Cost Stats",description:"Electricity cost per device, split by tariff zones",preview:!1}))}function Re(){document.querySelector("home-assistant")!==null&&!window.customElements.get("home-assistant")?(window.customElements.whenDefined("home-assistant").then(xt),setTimeout(()=>{window.customElements.get(x)||(console.warn(`${x}: the frontend did not boot in time; defining the card anyway`),xt())},Pe)):xt()}Re();export{Pe as BOOT_TIMEOUT_MS,xt as defineCard,Re as registerCard};
