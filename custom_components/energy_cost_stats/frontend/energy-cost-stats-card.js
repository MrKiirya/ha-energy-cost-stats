var F=globalThis,G=F.ShadowRoot&&(F.ShadyCSS===void 0||F.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ct=Symbol(),Tt=new WeakMap,N=class{constructor(t,e,r){if(this._$cssResult$=!0,r!==ct)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(G&&t===void 0){let r=e!==void 0&&e.length===1;r&&(t=Tt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),r&&Tt.set(e,t))}return t}toString(){return this.cssText}},Pt=n=>new N(typeof n=="string"?n:n+"",void 0,ct),dt=(n,...t)=>{let e=n.length===1?n[0]:t.reduce((r,s,i)=>r+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+n[i+1],n[0]);return new N(e,n,ct)},Rt=(n,t)=>{if(G)n.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let r=document.createElement("style"),s=F.litNonce;s!==void 0&&r.setAttribute("nonce",s),r.textContent=e.cssText,n.appendChild(r)}},lt=G?n=>n:n=>n instanceof CSSStyleSheet?(t=>{let e="";for(let r of t.cssRules)e+=r.cssText;return Pt(e)})(n):n;var{is:ae,defineProperty:ce,getOwnPropertyDescriptor:de,getOwnPropertyNames:le,getOwnPropertySymbols:ue,getPrototypeOf:pe}=Object,j=globalThis,Dt=j.trustedTypes,he=Dt?Dt.emptyScript:"",me=j.reactiveElementPolyfillSupport,U=(n,t)=>n,ut={toAttribute(n,t){switch(t){case Boolean:n=n?he:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,t){let e=n;switch(t){case Boolean:e=n!==null;break;case Number:e=n===null?null:Number(n);break;case Object:case Array:try{e=JSON.parse(n)}catch{e=null}}return e}},Nt=(n,t)=>!ae(n,t),Mt={attribute:!0,type:String,converter:ut,reflect:!1,useDefault:!1,hasChanged:Nt};Symbol.metadata??=Symbol("metadata"),j.litPropertyMetadata??=new WeakMap;var y=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Mt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let r=Symbol(),s=this.getPropertyDescriptor(t,r,e);s!==void 0&&ce(this.prototype,t,s)}}static getPropertyDescriptor(t,e,r){let{get:s,set:i}=de(this.prototype,t)??{get(){return this[e]},set(o){this[e]=o}};return{get:s,set(o){let c=s?.call(this);i?.call(this,o),this.requestUpdate(t,c,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Mt}static _$Ei(){if(this.hasOwnProperty(U("elementProperties")))return;let t=pe(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(U("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(U("properties"))){let e=this.properties,r=[...le(e),...ue(e)];for(let s of r)this.createProperty(s,e[s])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[r,s]of e)this.elementProperties.set(r,s)}this._$Eh=new Map;for(let[e,r]of this.elementProperties){let s=this._$Eu(e,r);s!==void 0&&this._$Eh.set(s,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let r=new Set(t.flat(1/0).reverse());for(let s of r)e.unshift(lt(s))}else t!==void 0&&e.push(lt(t));return e}static _$Eu(t,e){let r=e.attribute;return r===!1?void 0:typeof r=="string"?r:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let r of e.keys())this.hasOwnProperty(r)&&(t.set(r,this[r]),delete this[r]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Rt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,r){this._$AK(t,r)}_$ET(t,e){let r=this.constructor.elementProperties.get(t),s=this.constructor._$Eu(t,r);if(s!==void 0&&r.reflect===!0){let i=(r.converter?.toAttribute!==void 0?r.converter:ut).toAttribute(e,r.type);this._$Em=t,i==null?this.removeAttribute(s):this.setAttribute(s,i),this._$Em=null}}_$AK(t,e){let r=this.constructor,s=r._$Eh.get(t);if(s!==void 0&&this._$Em!==s){let i=r.getPropertyOptions(s),o=typeof i.converter=="function"?{fromAttribute:i.converter}:i.converter?.fromAttribute!==void 0?i.converter:ut;this._$Em=s;let c=o.fromAttribute(e,i.type);this[s]=c??this._$Ej?.get(s)??c,this._$Em=null}}requestUpdate(t,e,r,s=!1,i){if(t!==void 0){let o=this.constructor;if(s===!1&&(i=this[t]),r??=o.getPropertyOptions(t),!((r.hasChanged??Nt)(i,e)||r.useDefault&&r.reflect&&i===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,r))))return;this.C(t,e,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:r,reflect:s,wrapped:i},o){r&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),i!==!0||o!==void 0)||(this._$AL.has(t)||(this.hasUpdated||r||(e=void 0),this._$AL.set(t,e)),s===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[s,i]of this._$Ep)this[s]=i;this._$Ep=void 0}let r=this.constructor.elementProperties;if(r.size>0)for(let[s,i]of r){let{wrapped:o}=i,c=this[s];o!==!0||this._$AL.has(s)||c===void 0||this.C(s,void 0,i,c)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(e)):this._$EM()}catch(r){throw t=!1,this._$EM(),r}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};y.elementStyles=[],y.shadowRootOptions={mode:"open"},y[U("elementProperties")]=new Map,y[U("finalized")]=new Map,me?.({ReactiveElement:y}),(j.reactiveElementVersions??=[]).push("2.1.2");var ht=globalThis,Ut=n=>n,K=ht.trustedTypes,Lt=K?K.createPolicy("lit-html",{createHTML:n=>n}):void 0,mt="$lit$",v=`lit$${Math.random().toFixed(9).slice(2)}$`,gt="?"+v,ge=`<${gt}>`,E=document,H=()=>E.createComment(""),O=n=>n===null||typeof n!="object"&&typeof n!="function",_t=Array.isArray,qt=n=>_t(n)||typeof n?.[Symbol.iterator]=="function",pt=`[ 	
\f\r]`,L=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ht=/-->/g,Ot=/>/g,S=RegExp(`>|${pt}(?:([^\\s"'>=/]+)(${pt}*=${pt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),It=/'/g,zt=/"/g,Ft=/^(?:script|style|textarea|title)$/i,ft=n=>(t,...e)=>({_$litType$:n,strings:t,values:e}),u=ft(1),He=ft(2),Oe=ft(3),f=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),Bt=new WeakMap,C=E.createTreeWalker(E,129);function Gt(n,t){if(!_t(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return Lt!==void 0?Lt.createHTML(t):t}var jt=(n,t)=>{let e=n.length-1,r=[],s,i=t===2?"<svg>":t===3?"<math>":"",o=L;for(let c=0;c<e;c++){let a=n[c],d,p,h=-1,m=0;for(;m<a.length&&(o.lastIndex=m,p=o.exec(a),p!==null);)m=o.lastIndex,o===L?p[1]==="!--"?o=Ht:p[1]!==void 0?o=Ot:p[2]!==void 0?(Ft.test(p[2])&&(s=RegExp("</"+p[2],"g")),o=S):p[3]!==void 0&&(o=S):o===S?p[0]===">"?(o=s??L,h=-1):p[1]===void 0?h=-2:(h=o.lastIndex-p[2].length,d=p[1],o=p[3]===void 0?S:p[3]==='"'?zt:It):o===zt||o===It?o=S:o===Ht||o===Ot?o=L:(o=S,s=void 0);let g=o===S&&n[c+1].startsWith("/>")?" ":"";i+=o===L?a+ge:h>=0?(r.push(d),a.slice(0,h)+mt+a.slice(h)+v+g):a+v+(h===-2?c:g)}return[Gt(n,i+(n[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),r]},I=class n{constructor({strings:t,_$litType$:e},r){let s;this.parts=[];let i=0,o=0,c=t.length-1,a=this.parts,[d,p]=jt(t,e);if(this.el=n.createElement(d,r),C.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(s=C.nextNode())!==null&&a.length<c;){if(s.nodeType===1){if(s.hasAttributes())for(let h of s.getAttributeNames())if(h.endsWith(mt)){let m=p[o++],g=s.getAttribute(h).split(v),A=/([.?@])?(.*)/.exec(m);a.push({type:1,index:i,name:A[2],strings:g,ctor:A[1]==="."?Z:A[1]==="?"?Y:A[1]==="@"?W:T}),s.removeAttribute(h)}else h.startsWith(v)&&(a.push({type:6,index:i}),s.removeAttribute(h));if(Ft.test(s.tagName)){let h=s.textContent.split(v),m=h.length-1;if(m>0){s.textContent=K?K.emptyScript:"";for(let g=0;g<m;g++)s.append(h[g],H()),C.nextNode(),a.push({type:2,index:++i});s.append(h[m],H())}}}else if(s.nodeType===8)if(s.data===gt)a.push({type:2,index:i});else{let h=-1;for(;(h=s.data.indexOf(v,h+1))!==-1;)a.push({type:7,index:i}),h+=v.length-1}i++}}static createElement(t,e){let r=E.createElement("template");return r.innerHTML=t,r}};function k(n,t,e=n,r){if(t===f)return t;let s=r!==void 0?e._$Co?.[r]:e._$Cl,i=O(t)?void 0:t._$litDirective$;return s?.constructor!==i&&(s?._$AO?.(!1),i===void 0?s=void 0:(s=new i(n),s._$AT(n,e,r)),r!==void 0?(e._$Co??=[])[r]=s:e._$Cl=s),s!==void 0&&(t=k(n,s._$AS(n,t.values),s,r)),t}var V=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:r}=this._$AD,s=(t?.creationScope??E).importNode(e,!0);C.currentNode=s;let i=C.nextNode(),o=0,c=0,a=r[0];for(;a!==void 0;){if(o===a.index){let d;a.type===2?d=new D(i,i.nextSibling,this,t):a.type===1?d=new a.ctor(i,a.name,a.strings,this,t):a.type===6&&(d=new Q(i,this,t)),this._$AV.push(d),a=r[++c]}o!==a?.index&&(i=C.nextNode(),o++)}return C.currentNode=E,s}p(t){let e=0;for(let r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(t,r,e),e+=r.strings.length-2):r._$AI(t[e])),e++}},D=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,r,s){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=r,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=k(this,t,e),O(t)?t===l||t==null||t===""?(this._$AH!==l&&this._$AR(),this._$AH=l):t!==this._$AH&&t!==f&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):qt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==l&&O(this._$AH)?this._$AA.nextSibling.data=t:this.T(E.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:r}=t,s=typeof r=="number"?this._$AC(t):(r.el===void 0&&(r.el=I.createElement(Gt(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===s)this._$AH.p(e);else{let i=new V(s,this),o=i.u(this.options);i.p(e),this.T(o),this._$AH=i}}_$AC(t){let e=Bt.get(t.strings);return e===void 0&&Bt.set(t.strings,e=new I(t)),e}k(t){_t(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,r,s=0;for(let i of t)s===e.length?e.push(r=new n(this.O(H()),this.O(H()),this,this.options)):r=e[s],r._$AI(i),s++;s<e.length&&(this._$AR(r&&r._$AB.nextSibling,s),e.length=s)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let r=Ut(t).nextSibling;Ut(t).remove(),t=r}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},T=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,r,s,i){this.type=1,this._$AH=l,this._$AN=void 0,this.element=t,this.name=e,this._$AM=s,this.options=i,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=l}_$AI(t,e=this,r,s){let i=this.strings,o=!1;if(i===void 0)t=k(this,t,e,0),o=!O(t)||t!==this._$AH&&t!==f,o&&(this._$AH=t);else{let c=t,a,d;for(t=i[0],a=0;a<i.length-1;a++)d=k(this,c[r+a],e,a),d===f&&(d=this._$AH[a]),o||=!O(d)||d!==this._$AH[a],d===l?t=l:t!==l&&(t+=(d??"")+i[a+1]),this._$AH[a]=d}o&&!s&&this.j(t)}j(t){t===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Z=class extends T{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===l?void 0:t}},Y=class extends T{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==l)}},W=class extends T{constructor(t,e,r,s,i){super(t,e,r,s,i),this.type=5}_$AI(t,e=this){if((t=k(this,t,e,0)??l)===f)return;let r=this._$AH,s=t===l&&r!==l||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,i=t!==l&&(r===l||s);s&&this.element.removeEventListener(this.name,this,r),i&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},Q=class{constructor(t,e,r){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(t){k(this,t)}},Kt={M:mt,P:v,A:gt,C:1,L:jt,R:V,D:qt,V:k,I:D,H:T,N:Y,U:W,B:Z,F:Q},_e=ht.litHtmlPolyfillSupport;_e?.(I,D),(ht.litHtmlVersions??=[]).push("3.3.3");var Vt=(n,t,e)=>{let r=e?.renderBefore??t,s=r._$litPart$;if(s===void 0){let i=e?.renderBefore??null;r._$litPart$=s=new D(t.insertBefore(H(),i),i,void 0,e??{})}return s._$AI(n),s};var $t=globalThis,b=class extends y{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Vt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return f}};b._$litElement$=!0,b.finalized=!0,$t.litElementHydrateSupport?.({LitElement:b});var fe=$t.litElementPolyfillSupport;fe?.({LitElement:b});($t.litElementVersions??=[]).push("4.2.2");var P={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Zt=n=>(...t)=>({_$litDirective$:n,values:t}),J=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,r){this._$Ct=t,this._$AM=e,this._$Ci=r}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var{I:Xe}=Kt;var Yt=n=>n.strings===void 0;var $e={},Wt=(n,t=$e)=>n._$AH=t;var X=Zt(class extends J{constructor(n){if(super(n),n.type!==P.PROPERTY&&n.type!==P.ATTRIBUTE&&n.type!==P.BOOLEAN_ATTRIBUTE)throw Error("The `live` directive is not allowed on child or event bindings");if(!Yt(n))throw Error("`live` bindings can only contain a single expression")}render(n){return n}update(n,[t]){if(t===f||t===l)return t;let e=n.element,r=n.name;if(n.type===P.PROPERTY){if(t===e[r])return f}else if(n.type===P.BOOLEAN_ATTRIBUTE){if(!!t===e.hasAttribute(r))return f}else if(n.type===P.ATTRIBUTE&&e.getAttribute(r)===t+"")return f;return Wt(n),t}});var B=["today","yesterday","this_week","last_week","this_month","last_month","this_quarter","this_year","now-7d","now-30d","now-12m"];function $(n){let t=/^(\d{4})-(\d{2})-(\d{2})$/.exec(n);if(!t)throw new Error(`invalid date: ${n}`);let[,e,r,s]=t;return new Date(Date.UTC(Number(e),Number(r)-1,Number(s)))}function tt(n){return n.toISOString().slice(0,10)}function vt(n){try{return tt($(n))===n}catch{return!1}}function _(n,t){return tt(new Date($(n).getTime()+t*864e5))}function M(n,t=0){let e=$(n);return tt(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t,1)))}function R(n,t=0){let e=$(n);return tt(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t+1,0)))}function yt(n){let t=($(n).getUTCDay()+6)%7;return _(n,-t)}function q(n){return Math.round(($(n.end).getTime()-$(n.start).getTime())/864e5)+1}function wt(n){let t=$(n.start);if(t.getUTCDate()!==1||R(n.end)!==n.end)return null;let e=$(n.end);return(e.getUTCFullYear()-t.getUTCFullYear())*12+(e.getUTCMonth()-t.getUTCMonth())+1}function et(n,t=new Date){let e={year:"numeric",month:"2-digit",day:"2-digit"},r;try{r=new Intl.DateTimeFormat("en-CA",{...e,timeZone:n}).formatToParts(t)}catch{r=new Intl.DateTimeFormat("en-CA",e).formatToParts(t)}let s=i=>r.find(o=>o.type===i)?.value??"";return`${s("year")}-${s("month")}-${s("day")}`}function w(n,t){switch(n){case"today":return{start:t,end:t};case"yesterday":{let e=_(t,-1);return{start:e,end:e}}case"this_week":{let e=yt(t);return{start:e,end:_(e,6)}}case"last_week":{let e=_(yt(t),-7);return{start:e,end:_(e,6)}}case"this_month":return{start:M(t),end:R(t)};case"last_month":return{start:M(t,-1),end:R(t,-1)};case"this_quarter":{let e=$(t).getUTCMonth(),r=M(t,-(e%3));return{start:r,end:R(r,2)}}case"this_year":{let e=t.slice(0,4);return{start:`${e}-01-01`,end:`${e}-12-31`}}case"now-7d":return{start:_(t,-6),end:t};case"now-30d":return{start:_(t,-29),end:t};case"now-12m":return{start:M(t,-11),end:R(t)}}}function bt(n){let t=wt(n);if(t!==null){let r=$(n.start).getUTCMonth();return t===1?"month":t===3&&r%3===0?"quarter":t===12&&r===0?"year":"months"}let e=q(n);return e===1?"day":e===7&&yt(n.start)===n.start?"week":"days"}function xt(n,t){let e=wt(n);if(e!==null){let s=e*t;return{start:M(n.start,s),end:R(n.end,s)}}let r=q(n)*t;return{start:_(n.start,r),end:_(n.end,r)}}function Qt(n,t){switch(bt(n)){case"day":return w("today",t);case"week":return w("this_week",t);case"month":return w("this_month",t);case"quarter":return w("this_quarter",t);case"year":return w("this_year",t);case"months":{let r=wt(n)??1;return{start:M(t,-(r-1)),end:R(t)}}case"days":return{start:_(t,-(q(n)-1)),end:t}}}function rt(n,t){return n.start<=t&&t<=n.end}function z(n){return _(n.end,1)}function nt(n,t,e=new Date){let r=et(t,e);if(!rt(n,r))return z(n);let s;try{s=new Intl.DateTimeFormat("en-GB",{timeZone:t,hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(e)}catch{return z(n)}let i=Number(s.find(d=>d.type==="hour")?.value),o=Number(s.find(d=>d.type==="minute")?.value);if(!Number.isFinite(i)||o!==e.getUTCMinutes())return z(n);let c=n.start===r?Math.max(i,1):i,a=ye(t,e,c-i);return`${r}T${String(c).padStart(2,"0")}:00:00${a}`}function ye(n,t,e){let r=new Date(t.getTime()+e*36e5),s=new Intl.DateTimeFormat("en-US",{timeZone:n,timeZoneName:"longOffset"}).formatToParts(r).find(o=>o.type==="timeZoneName")?.value??"GMT",i=/^GMT([+-]\d{2}):?(\d{2})?$/.exec(s);return i?`${i[1]}:${i[2]??"00"}`:"+00:00"}var ve=31;function Jt(n){let t=q(n);return t<=2?"hour":t<=45?"day":t<=120?"week":"month"}function st(n,t){return n!=="hour"||q(t)<=ve}var we={title:"Energy cost",previous:"Previous",next:"Next",now:"Now",refresh:"Refresh",period:"Period",custom:"Custom period",from:"From",to:"To",apply:"Apply",grouping:"Grouping","grouping.auto":"Auto","grouping.hour":"Hours","grouping.day":"Days","grouping.week":"Weeks","grouping.month":"Months","grouping.hour_too_long":"Hours: up to 31 days","preset.today":"Today","preset.yesterday":"Yesterday","preset.this_week":"This week","preset.last_week":"Last week","preset.this_month":"This month","preset.last_month":"Last month","preset.this_quarter":"This quarter","preset.this_year":"This year","preset.now-7d":"Last 7 days","preset.now-30d":"Last 30 days","preset.now-12m":"Last 12 months",device:"Device",total:"Total",kwh:"kWh",cost:"Cost",avg_price:"Avg. price",breakdown:"By period",breakdown_device:"Show",all_devices:"All devices",data_quality:"Data quality",loading:"Loading…",no_devices:"No energy sensors selected. Add them in the integration options.",no_plan:"No tariff plan covers this period: costs are unknown.",unpriced:"{hours} h before the first tariff plan are not priced.","status.complete":"Complete","status.estimated":"Contains estimated hours (spread over a data gap)","status.partial":"Some hours are missing","status.missing":"No data","issue.estimated":"estimated","issue.excluded_negative":"excluded (negative)","issue.excluded_spike":"excluded (spike)","statistics.no_statistics":"no statistics yet","statistics.unsupported":"unsupported sensor","error.not_loaded":"Energy Cost Stats is not set up or not loaded.","error.invalid_period":"Invalid period.","error.period_too_long":"The period is too long for this grouping.","error.unknown_entity":"The card lists a sensor that is not selected in the integration.","error.unknown_command":"The integration is not loaded (restart Home Assistant after installing).","error.generic":"Could not load the report: {message}","compare.title":"Tariff comparison","compare.tariff":"Tariff","compare.actual":"Actual","compare.difference":"Difference","compare.empty":"No tariffs to compare. Choose them in the integration options (Configure → Compare).","compare.unpriced":"{hours} h not priced by this tariff — the difference covers only the priced hours","compare.unpriced_actual":"{hours} h not priced by the actual schedule — the difference covers only the priced hours","compare.error":"Could not load the comparison: {message}","error.unknown_tariff":"A tariff in the comparison list is not defined in the integration.","nested.title":"Measured inside {name}; not counted again in the total","nested.note":"Indented rows are measured inside the device above them. The total counts their energy only for hours where the device above has no data.",coverage:"{measured} measured, {estimated} estimated, {excluded} excluded, {missing} missing of {expected} h"},be={title:"Стоимость электроэнергии",previous:"Назад",next:"Вперёд",now:"Сейчас",refresh:"Обновить",period:"Период",custom:"Свой период",from:"С",to:"По",apply:"Применить",grouping:"Группировка","grouping.auto":"Авто","grouping.hour":"По часам","grouping.day":"По дням","grouping.week":"По неделям","grouping.month":"По месяцам","grouping.hour_too_long":"По часам: до 31 дня","preset.today":"Сегодня","preset.yesterday":"Вчера","preset.this_week":"Эта неделя","preset.last_week":"Прошлая неделя","preset.this_month":"Этот месяц","preset.last_month":"Прошлый месяц","preset.this_quarter":"Этот квартал","preset.this_year":"Этот год","preset.now-7d":"Последние 7 дней","preset.now-30d":"Последние 30 дней","preset.now-12m":"Последние 12 месяцев",device:"Устройство",total:"Итого",kwh:"кВт·ч",cost:"Сумма",avg_price:"Ср. цена",breakdown:"По периодам",breakdown_device:"Показать",all_devices:"Все устройства",data_quality:"Качество данных",loading:"Загрузка…",no_devices:"Не выбраны датчики энергии. Добавьте их в настройках интеграции.",no_plan:"Для этого периода нет тарифного плана: стоимость неизвестна.",unpriced:"{hours} ч до первого тарифного плана не оценены.","status.complete":"Полные данные","status.estimated":"Есть оценочные часы (распределены по пропуску)","status.partial":"Часть часов отсутствует","status.missing":"Нет данных","issue.estimated":"оценка","issue.excluded_negative":"исключено (отрицательное)","issue.excluded_spike":"исключено (выброс)","statistics.no_statistics":"статистики пока нет","statistics.unsupported":"датчик не поддерживается","error.not_loaded":"Energy Cost Stats не настроена или не загружена.","error.invalid_period":"Неверный период.","error.period_too_long":"Период слишком длинный для этой группировки.","error.unknown_entity":"В карточке указан датчик, не выбранный в интеграции.","error.unknown_command":"Интеграция не загружена (перезапустите Home Assistant после установки).","error.generic":"Не удалось загрузить отчёт: {message}","compare.title":"Сравнение тарифов","compare.tariff":"Тариф","compare.actual":"Фактически","compare.difference":"Разница","compare.empty":"Нет тарифов для сравнения. Выберите их в настройках интеграции (Настроить → Сравнение).","compare.unpriced":"{hours} ч не оценены этим тарифом — разница учитывает только оценённые часы","compare.unpriced_actual":"{hours} ч не оценены фактическим расписанием — разница учитывает только оценённые часы","compare.error":"Не удалось загрузить сравнение: {message}","error.unknown_tariff":"Тариф из списка сравнения не определён в интеграции.","nested.title":"Измеряется внутри «{name}»; в итоге повторно не учитывается","nested.note":"Строки со сдвигом измеряются внутри устройства выше. Итог учитывает их энергию только за часы, когда у устройства выше нет данных.",coverage:"{measured} измерено, {estimated} оценено, {excluded} исключено, {missing} нет из {expected} ч"},it=class{constructor(t){this.locale=t||"en",this.table=this.locale.toLowerCase().startsWith("ru")?be:we}t(t,e={}){return this.table[t].replace(/\{(\w+)\}/g,(r,s)=>s in e?String(e[s]):`{${s}}`)}preset(t){return this.t(`preset.${t}`)}grouping(t){return this.t(`grouping.${t}`)}number(t,e){return t==null?"—":new Intl.NumberFormat(this.locale,{minimumFractionDigits:e,maximumFractionDigits:e}).format(Number(t))}money(t,e,r=!1){if(t==null)return"—";if(e)try{return new Intl.NumberFormat(this.locale,{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:2,...r?{signDisplay:"exceptZero"}:{}}).format(Number(t))}catch{}return r?new Intl.NumberFormat(this.locale,{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero"}).format(Number(t)):this.number(t,2)}signedMoney(t,e){return t===null?"—":this.money(String(t),e,!0)}signedPercent(t){return t===null?"—":`${new Intl.NumberFormat(this.locale,{minimumFractionDigits:1,maximumFractionDigits:1,signDisplay:"exceptZero"}).format(t)} %`}avgPrice(t,e){return t===null||e===null||Number(e)===0?"—":this.number(String(Number(t)/Number(e)),2)}date(t,e){return new Intl.DateTimeFormat(this.locale,{...e,timeZone:"UTC"}).format(new Date(`${t}T00:00:00Z`))}periodLabel(t){switch(bt(t)){case"day":return this.date(t.start,{day:"numeric",month:"long",year:"numeric"});case"month":return this.date(t.start,{month:"long",year:"numeric"});case"quarter":return`Q${Math.floor(Number(t.start.slice(5,7))/3)+1} ${t.start.slice(0,4)}`;case"year":return t.start.slice(0,4);case"months":return`${this.date(t.start,{month:"short",year:"numeric"})} – ${this.date(t.end,{month:"short",year:"numeric"})}`;default:{let r=t.start.slice(0,4)===t.end.slice(0,4),s=this.date(t.start,{day:"numeric",month:"short",...r?{}:{year:"numeric"}}),i=this.date(t.end,{day:"numeric",month:"short",year:"numeric"});return`${s} – ${i}`}}}bucketLabel(t,e){let r=t.slice(0,10);switch(e){case"hour":return`${this.date(r,{day:"numeric",month:"short"})} ${t.slice(11,16)}`;case"day":return this.date(r,{weekday:"short",day:"numeric",month:"short"});case"week":return this.date(r,{day:"numeric",month:"short",year:"numeric"});case"month":return this.date(r,{month:"long",year:"numeric"});default:return this.t("total")}}};function Xt(n,t){if(n===null||t===null)return{amount:null,percent:null};let e=Number(n),r=Number(t);if(!Number.isFinite(e)||!Number.isFinite(r))return{amount:null,percent:null};let s=r-e;return{amount:s,percent:e===0?null:s/e*100}}function te(n){let t=new Set(n.map(c=>c.entity_id)),e=new Map,r=[];for(let c of n){let a=c.upstream;if(a&&a!==c.entity_id&&t.has(a)){let d=e.get(a)??[];d.push(c.entity_id),e.set(a,d)}else r.push(c.entity_id)}let s=[],i=new Set,o=(c,a)=>{if(!i.has(c)){i.add(c),s.push({entity_id:c,depth:a});for(let d of e.get(c)??[])o(d,a+1)}};for(let c of r)o(c,0);for(let c of n)o(c.entity_id,0);return s}function ee(n,t){return t===void 0||n===void 0?n!==t:n.language!==t.language||n.locale?.language!==t.locale?.language||n.config?.time_zone!==t.config?.time_zone}var xe="energy_cost_stats/report",Ae="energy_cost_stats/compare";function re(n,t){let e={type:n,start:t.period.start,end:nt(t.period,t.timeZone,t.now)};return t.entities&&t.entities.length>0&&(e.entities=t.entities),e}function Se(n){let{type:t,start:e,end:r,entities:s}=re(xe,n),i={type:t,start:e,end:r,grouping:n.grouping};return s!==void 0&&(i.entities=s),i}function Ce(n){return re(Ae,n)}function ne(n,t){return n.callWS(Ce(t))}function se(n,t){return n.callWS(Se(t))}function ot(n){if(n&&typeof n=="object"&&"code"in n){let t=n.code;return typeof t=="string"?t:void 0}}function At(n){return n&&typeof n=="object"&&"message"in n?String(n.message):String(n)}var x="energy-cost-stats-card",ie=["auto","hour","day","week","month"],Ee=600*1e3,ke="M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",Te="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",Pe="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";function St(n){return u`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${n}></path></svg>`}var at=class extends b{constructor(){super(...arguments);this._groupingChoice="auto";this._compareLoading=!1;this._compareHidden=!1;this._loading=!1;this._customOpen=!1;this._customStart="";this._customEnd="";this._breakdownEntity="";this._requestSeq=0;this._compareSeq=0;this._lastRequestOpen=!1}static{this.properties={hass:{attribute:!1,hasChanged:ee},_config:{state:!0},_period:{state:!0},_groupingChoice:{state:!0},_report:{state:!0},_compare:{state:!0},_compareError:{state:!0},_compareLoading:{state:!0},_compareHidden:{state:!0},_error:{state:!0},_loading:{state:!0},_customOpen:{state:!0},_customStart:{state:!0},_customEnd:{state:!0},_breakdownEntity:{state:!0}}}static getStubConfig(){return{type:`custom:${x}`,period:"this_month"}}setConfig(e){if(!e||typeof e!="object")throw new Error("Invalid configuration");if(e.period!==void 0&&!B.includes(e.period))throw new Error(`Unknown period: ${String(e.period)}`);if(e.grouping!==void 0&&!ie.includes(e.grouping))throw new Error(`Unknown grouping: ${String(e.grouping)}`);if(e.entities!==void 0&&(!Array.isArray(e.entities)||e.entities.some(s=>typeof s!="string")))throw new Error("entities must be a list of entity ids");let r=this._config;this._config=e,this._groupingChoice=e.grouping??"auto",r&&this._period&&(this._period=void 0,this._report=void 0,this._compare=void 0)}getCardSize(){let e=this._compare&&!this._compareHidden?this._compare.tariffs.length+3:0;return 3+(this._report?.devices.length??2)+e}getGridOptions(){return{columns:"full",min_columns:6}}get _strings(){return new it(this.hass?.locale?.language??this.hass?.language)}get _timeZone(){return this._reportTimeZone??this.hass?.config?.time_zone}_today(){return et(this._timeZone)}get grouping(){let e=this._period;if(!e)return"day";let r=this._groupingChoice;return r!=="auto"&&st(r,e)?r:Jt(e)}connectedCallback(){super.connectedCallback(),this._timer=setInterval(()=>{this._period&&this._lastRequestOpen&&!this._loading&&this._load()},Ee)}disconnectedCallback(){super.disconnectedCallback(),this._timer!==void 0&&clearInterval(this._timer),this._timer=void 0}willUpdate(e){this.hass&&this._config&&!this._period&&(this._period=w(this._config.period??"this_month",this._today())),super.willUpdate(e)}updated(e){super.updated(e),!(!this.hass||!this._period)&&(e.has("_period")||e.has("hass")&&e.get("hass")===void 0?this._load():e.has("_groupingChoice")&&this._loadReport())}_load(){return this._loadCompare(),this._loadReport()}async _loadCompare(){let e=this.hass,r=this._period;if(!e||!r)return;let s=++this._compareSeq;this._compareLoading=!0;try{let i=await ne(e,{period:r,entities:this._config?.entities,timeZone:this._timeZone});if(s!==this._compareSeq)return;this._compare=i,this._compareError=void 0,this._compareHidden=!1}catch(i){if(s!==this._compareSeq)return;if(this._compare=void 0,ot(i)==="unknown_command"){this._compareHidden=!0,this._compareError=void 0;return}this._compareHidden=!1,this._compareError=this._strings.t("compare.error",{message:this._errorMessage(i)})}finally{s===this._compareSeq&&(this._compareLoading=!1)}}_errorMessage(e){let r=ot(e),i=r?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_tariff:"error.unknown_tariff"}[r]:void 0;return i?this._strings.t(i):At(e)}async _loadReport(){let e=this.hass,r=this._period;if(!e||!r)return;let s=++this._requestSeq,i=this._timeZone;this._loading=!0;try{let o=await se(e,{period:r,grouping:this.grouping,entities:this._config?.entities,timeZone:i});if(s!==this._requestSeq)return;this._report=o,this._error=void 0,this._reportTimeZone=o.time_zone,this._lastRequestOpen=nt(r,o.time_zone)!==z(r),o.time_zone!==i&&rt(r,et(o.time_zone))&&this._load()}catch(o){if(s!==this._requestSeq)return;let c=ot(o),d=c?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_command:"error.unknown_command"}[c]:void 0;this._error=d?this._strings.t(d):this._strings.t("error.generic",{message:At(o)}),this._report=void 0}finally{s===this._requestSeq&&(this._loading=!1)}}_selectedPreset(){if(!this._period)return"";let e=this._today(),r=this._period;return B.find(s=>{let i=w(s,e);return i.start===r.start&&i.end===r.end})??""}_onPreset(e){let r=e.target.value;if(r==="custom"){this._openCustom();return}B.includes(r)&&(this._customOpen=!1,this._period=w(r,this._today()))}_openCustom(){this._customOpen=!0,this._customStart=this._period?.start??this._today(),this._customEnd=this._period?.end??this._today()}_applyCustom(){let e=this._customStart,r=this._customEnd;!vt(e)||!vt(r)||(this._period=e<=r?{start:e,end:r}:{start:r,end:e},this._customOpen=!1)}_shift(e){this._period&&(this._period=xt(this._period,e))}_now(){this._period&&(this._period=Qt(this._period,this._today()))}_onGrouping(e){this._groupingChoice=e.target.value}render(){if(!this._config||!this.hass||!this._period)return l;let e=this._strings,r=this._config.title??e.t("title");return u`
      <ha-card>
        <div class="header">
          <div class="title">${r}</div>
          ${this._loading?u`<div class="loading" role="status">${e.t("loading")}</div>`:l}
        </div>
        ${this._renderPicker(e)}
        <div class="content">
          ${this._error?u`<div class="error" role="alert">${this._error}</div>`:this._report?this._renderReport(e,this._report):l}
        </div>
      </ha-card>
    `}_renderPicker(e){let r=this._period,s=this._selectedPreset(),i=this._today(),o=rt(r,i),c=xt(r,1).start>i;return u`
      <div class="picker">
        <select
          class="preset"
          aria-label=${e.t("period")}
          .value=${X(s)}
          @change=${this._onPreset}
        >
          <option value="" ?hidden=${s!==""} ?selected=${s===""}>
            ${e.t("custom")}
          </option>
          ${B.map(a=>u`<option value=${a} ?selected=${a===s}>${e.preset(a)}</option>`)}
          <option value="custom">${e.t("custom")}…</option>
        </select>
        <div class="nav">
          <button
            class="icon prev"
            title=${e.t("previous")}
            aria-label=${e.t("previous")}
            @click=${()=>this._shift(-1)}
          >
            ${St(ke)}
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
            ${St(Te)}
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
          ${St(Pe)}
        </button>
      </div>
      ${this._customOpen?u`<div class="custom">
            <label
              >${e.t("from")}
              <input
                type="date"
                class="custom-start"
                .value=${this._customStart}
                max=${i}
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
    `}_renderReport(e,r){if(r.devices.length===0)return u`<div class="note">${e.t("no_devices")}</div>`;let s=new Map(r.devices.map(c=>[c.entity_id,c])),i=r.totals,o=r.plans.length===0;return u`
      ${o?u`<div class="note warning">${e.t("no_plan")}</div>`:l}
      ${!o&&r.unpriced_hours>0?u`<div class="note warning">
            ${e.t("unpriced",{hours:r.unpriced_hours})}
          </div>`:l}
      <div class="table-wrap">
        <table class="devices">
          ${this._renderHead(e,r,e.t("device"),i)}
          <tbody>
            ${this._deviceRows(r).map(({row:c,depth:a})=>{let d=c.entity_id?s.get(c.entity_id):void 0,p=d?.name??c.entity_id??"",h=d&&d.statistics!=="ok"?e.t(`statistics.${d.statistics}`):"",m=d?.upstream?s.get(d.upstream):void 0;return this._renderRow(e,r,c,p,h,{depth:a,title:a>0&&m?`${p} — ${e.t("nested.title",{name:m.name})}`:p})})}
          </tbody>
          <tfoot>
            ${this._renderRow(e,r,i.total,e.t("total"),"")}
          </tfoot>
        </table>
      </div>
      ${r.devices.some(c=>c.upstream&&s.has(c.upstream))?u`<div class="note nested-note">${e.t("nested.note")}</div>`:l}
      ${this._renderComparison(e,r)}
      ${r.grouping!=="total"?this._renderBreakdown(e,r):l}
      ${r.issues.length>0?this._renderIssues(e,r,s):l}
    `}_deviceRows(e){let r=new Map(e.totals.rows.map(o=>[o.entity_id,o])),s=[],i=new Set;for(let{entity_id:o,depth:c}of te(e.devices)){let a=r.get(o);a&&!i.has(a)&&(i.add(a),s.push({row:a,depth:c}))}for(let o of e.totals.rows)i.has(o)||s.push({row:o,depth:0});return s}_renderComparison(e,r){if(this._compareHidden)return l;let s=this._compare,i=this._compareError;if(!s&&!i)return l;let o=r.currency,c=l;if(i)c=u`<div class="error" role="alert">${i}</div>`;else if(s&&s.tariffs.length===0)c=u`<div class="note">${e.t("compare.empty")}</div>`;else if(s){let d=s.actual,p=d.totals.total,h=d.plans.map(m=>m.name).join(" → ");c=u`<div class="table-wrap">
        <table class="comparison">
          <thead>
            <tr>
              <th rowspan="2" class="name">${e.t("compare.tariff")}</th>
              <th rowspan="2" class="num">${e.t("cost")}</th>
              <th colspan="2" class="zone group-start">${e.t("compare.difference")}</th>
              <th rowspan="2" class="num group-start">${e.t("avg_price")}</th>
            </tr>
            <tr>
              <th class="num group-start">${o??""}</th>
              <th class="num">%</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row" class="name" title=${e.t("compare.actual")}>
                <span>${e.t("compare.actual")}</span>
                ${h?u`<span class="sub">${h}</span>`:l}
              </th>
              <td class="num strong">${e.money(p.cost,o)}</td>
              <td class="num group-start">—</td>
              <td class="num">—</td>
              <td class="num group-start">${e.avgPrice(p.cost,p.kwh)}</td>
            </tr>
            ${s.tariffs.map(m=>{let g=m.report.totals.total,A=Xt(p.cost,g.cost),Et=m.report.unpriced_hours,kt=Et||d.unpriced_hours,oe=e.t(Et>0?"compare.unpriced":"compare.unpriced_actual",{hours:kt});return u`<tr>
                <th scope="row" class="name" title=${m.name}>
                  <span>${m.name}</span>
                  ${kt>0?u`<span class="badge partial" title=${oe}
                        >!</span
                      >`:l}
                </th>
                <td class="num strong">${e.money(g.cost,o)}</td>
                <td class="num group-start">${e.signedMoney(A.amount,o)}</td>
                <td class="num">${e.signedPercent(A.percent)}</td>
                <td class="num group-start">${e.avgPrice(g.cost,g.kwh)}</td>
              </tr>`})}
          </tbody>
        </table>
      </div>`}let a=this._compareLoading;return u`<section
      class="comparison ${a?"loading":""}"
      aria-busy=${a?"true":"false"}
    >
      <h3>
        ${e.t("compare.title")}
        ${a?u`<span class="loading" role="status">${e.t("loading")}</span>`:l}
      </h3>
      ${c}
    </section>`}_renderHead(e,r,s,i){let o=r.currency;return u`
      <thead>
        <tr>
          <th rowspan="2" class="name">${s}</th>
          ${r.zones.map((c,a)=>{let d=i.total.zones[a]?.price??null;return u`<th colspan="2" class="zone group-start">
              ${c.name}${d!==null?u`<span class="price">${e.money(d,o)}</span>`:l}
            </th>`})}
          <th colspan="3" class="zone sum group-start">${e.t("total")}</th>
        </tr>
        <tr>
          ${r.zones.map(()=>u`<th class="num group-start">${e.t("kwh")}</th>
                <th class="num">${e.t("cost")}</th>`)}
          <th class="num group-start">${e.t("kwh")}</th>
          <th class="num">${e.t("cost")}</th>
          <th class="num">${e.t("avg_price")}</th>
        </tr>
      </thead>
    `}_renderRow(e,r,s,i,o,c={depth:0,title:i}){let a=r.currency,d=s.coverage,p=e.t("coverage",{measured:d.measured,estimated:d.estimated,excluded:d.excluded,missing:d.missing,expected:d.expected});return u`
      <tr class="status-${s.status} ${c.depth>0?"nested":""}">
        <th
          scope="row"
          class="name"
          title=${c.title}
          style=${c.depth>0?`--depth: ${c.depth}`:l}
        >
          <span>${c.depth>0?"↳ ":""}${i}</span>
          ${s.status!=="complete"?u`<span
                class="badge ${s.status}"
                title="${e.t(`status.${s.status}`)} · ${p}"
                >${s.status==="estimated"?"≈":"!"}</span
              >`:l}
          ${o?u`<span class="sub">${o}</span>`:l}
        </th>
        ${s.zones.map(h=>u`<td class="num group-start">${e.number(h.kwh,2)}</td>
              <td class="num">${e.money(h.cost,a)}</td>`)}
        <td class="num strong group-start">${e.number(s.kwh,2)}</td>
        <td class="num strong">${e.money(s.cost,a)}</td>
        <td class="num">${e.avgPrice(s.cost,s.kwh)}</td>
      </tr>
    `}_renderBreakdown(e,r){let s=this._breakdownEntity,i=s?r.devices.findIndex(d=>d.entity_id===s):-1,o=d=>(i>=0?d.rows.find(p=>p.entity_id===s):void 0)??d.total,c=this._groupingChoice,a=c==="auto"||st(c,this._period)?c:"auto";return u`
      <details class="breakdown" ?open=${this._config?.show_breakdown??!1}>
        <summary>${e.t("breakdown")}</summary>
        <div class="breakdown-controls">
          <label
            >${e.t("breakdown_device")}
            <select
              class="breakdown-device"
              .value=${X(i>=0?s:"")}
              @change=${d=>{this._breakdownEntity=d.target.value}}
            >
              <option value="">${e.t("all_devices")}</option>
              ${r.devices.map(d=>u`<option value=${d.entity_id} ?selected=${d.entity_id===s}>
                    ${d.name}
                  </option>`)}
            </select>
          </label>
          <label
            >${e.t("grouping")}
            <select class="grouping" .value=${X(a)} @change=${this._onGrouping}>
              ${ie.map(d=>{let p=d==="auto"||st(d,this._period);return u`<option
                  value=${d}
                  ?disabled=${!p}
                  ?selected=${d===a}
                >
                  ${p?e.grouping(d):e.t("grouping.hour_too_long")}
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
    `}_bucketLabel(e,r,s){if(r.grouping==="week"){let i=s.start.slice(0,10);return e.periodLabel({start:i,end:_(i,6)})}return e.bucketLabel(s.start,r.grouping)}_renderIssues(e,r,s){return u`
      <details class="issues">
        <summary>${e.t("data_quality")} (${r.issues.length})</summary>
        <ul>
          ${r.issues.map(i=>u`<li>
                <span class="who">${s.get(i.entity_id)?.name??i.entity_id}</span>:
                ${e.t(`issue.${i.kind}`)},
                ${e.bucketLabel(i.start,"hour")} – ${e.bucketLabel(i.end,"hour")}
                (${i.hours} h, ${e.number(i.kwh,3)} ${e.t("kwh")})
              </li>`)}
        </ul>
      </details>
    `}static{this.styles=dt`
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
  `}};var Re=3e4;function Ct(){let n=window.customElements;n.get(x)||(n.define(x,at),window.customCards=window.customCards??[],window.customCards.some(t=>t.type===x)||window.customCards.push({type:x,name:"Energy Cost Stats",description:"Electricity cost per device, split by tariff zones",preview:!1}))}function De(){document.querySelector("home-assistant")!==null&&!window.customElements.get("home-assistant")?(window.customElements.whenDefined("home-assistant").then(Ct),setTimeout(()=>{window.customElements.get(x)||(console.warn(`${x}: the frontend did not boot in time; defining the card anyway`),Ct())},Re)):Ct()}De();export{Re as BOOT_TIMEOUT_MS,Ct as defineCard,De as registerCard};
