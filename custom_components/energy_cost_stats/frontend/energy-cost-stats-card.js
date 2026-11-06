var q=globalThis,K=q.ShadowRoot&&(q.ShadyCSS===void 0||q.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,lt=Symbol(),Mt=new WeakMap,U=class{constructor(t,e,r){if(this._$cssResult$=!0,r!==lt)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(K&&t===void 0){let r=e!==void 0&&e.length===1;r&&(t=Mt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),r&&Mt.set(e,t))}return t}toString(){return this.cssText}},Nt=s=>new U(typeof s=="string"?s:s+"",void 0,lt),ut=(s,...t)=>{let e=s.length===1?s[0]:t.reduce((r,n,i)=>r+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+s[i+1],s[0]);return new U(e,s,lt)},Ot=(s,t)=>{if(K)s.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let r=document.createElement("style"),n=q.litNonce;n!==void 0&&r.setAttribute("nonce",n),r.textContent=e.cssText,s.appendChild(r)}},pt=K?s=>s:s=>s instanceof CSSStyleSheet?(t=>{let e="";for(let r of t.cssRules)e+=r.cssText;return Nt(e)})(s):s;var{is:de,defineProperty:le,getOwnPropertyDescriptor:ue,getOwnPropertyNames:pe,getOwnPropertySymbols:he,getPrototypeOf:me}=Object,V=globalThis,Ut=V.trustedTypes,ge=Ut?Ut.emptyScript:"",_e=V.reactiveElementPolyfillSupport,z=(s,t)=>s,ht={toAttribute(s,t){switch(t){case Boolean:s=s?ge:null;break;case Object:case Array:s=s==null?s:JSON.stringify(s)}return s},fromAttribute(s,t){let e=s;switch(t){case Boolean:e=s!==null;break;case Number:e=s===null?null:Number(s);break;case Object:case Array:try{e=JSON.parse(s)}catch{e=null}}return e}},Lt=(s,t)=>!de(s,t),zt={attribute:!0,type:String,converter:ht,reflect:!1,useDefault:!1,hasChanged:Lt};Symbol.metadata??=Symbol("metadata"),V.litPropertyMetadata??=new WeakMap;var v=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=zt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let r=Symbol(),n=this.getPropertyDescriptor(t,r,e);n!==void 0&&le(this.prototype,t,n)}}static getPropertyDescriptor(t,e,r){let{get:n,set:i}=ue(this.prototype,t)??{get(){return this[e]},set(o){this[e]=o}};return{get:n,set(o){let d=n?.call(this);i?.call(this,o),this.requestUpdate(t,d,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??zt}static _$Ei(){if(this.hasOwnProperty(z("elementProperties")))return;let t=me(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(z("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(z("properties"))){let e=this.properties,r=[...pe(e),...he(e)];for(let n of r)this.createProperty(n,e[n])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[r,n]of e)this.elementProperties.set(r,n)}this._$Eh=new Map;for(let[e,r]of this.elementProperties){let n=this._$Eu(e,r);n!==void 0&&this._$Eh.set(n,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let r=new Set(t.flat(1/0).reverse());for(let n of r)e.unshift(pt(n))}else t!==void 0&&e.push(pt(t));return e}static _$Eu(t,e){let r=e.attribute;return r===!1?void 0:typeof r=="string"?r:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let r of e.keys())this.hasOwnProperty(r)&&(t.set(r,this[r]),delete this[r]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Ot(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,r){this._$AK(t,r)}_$ET(t,e){let r=this.constructor.elementProperties.get(t),n=this.constructor._$Eu(t,r);if(n!==void 0&&r.reflect===!0){let i=(r.converter?.toAttribute!==void 0?r.converter:ht).toAttribute(e,r.type);this._$Em=t,i==null?this.removeAttribute(n):this.setAttribute(n,i),this._$Em=null}}_$AK(t,e){let r=this.constructor,n=r._$Eh.get(t);if(n!==void 0&&this._$Em!==n){let i=r.getPropertyOptions(n),o=typeof i.converter=="function"?{fromAttribute:i.converter}:i.converter?.fromAttribute!==void 0?i.converter:ht;this._$Em=n;let d=o.fromAttribute(e,i.type);this[n]=d??this._$Ej?.get(n)??d,this._$Em=null}}requestUpdate(t,e,r,n=!1,i){if(t!==void 0){let o=this.constructor;if(n===!1&&(i=this[t]),r??=o.getPropertyOptions(t),!((r.hasChanged??Lt)(i,e)||r.useDefault&&r.reflect&&i===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,r))))return;this.C(t,e,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:r,reflect:n,wrapped:i},o){r&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),i!==!0||o!==void 0)||(this._$AL.has(t)||(this.hasUpdated||r||(e=void 0),this._$AL.set(t,e)),n===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,i]of this._$Ep)this[n]=i;this._$Ep=void 0}let r=this.constructor.elementProperties;if(r.size>0)for(let[n,i]of r){let{wrapped:o}=i,d=this[n];o!==!0||this._$AL.has(n)||d===void 0||this.C(n,void 0,i,d)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(e)):this._$EM()}catch(r){throw t=!1,this._$EM(),r}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};v.elementStyles=[],v.shadowRootOptions={mode:"open"},v[z("elementProperties")]=new Map,v[z("finalized")]=new Map,_e?.({ReactiveElement:v}),(V.reactiveElementVersions??=[]).push("2.1.2");var gt=globalThis,Ht=s=>s,Z=gt.trustedTypes,It=Z?Z.createPolicy("lit-html",{createHTML:s=>s}):void 0,_t="$lit$",b=`lit$${Math.random().toFixed(9).slice(2)}$`,ft="?"+b,fe=`<${ft}>`,C=document,H=()=>C.createComment(""),I=s=>s===null||typeof s!="object"&&typeof s!="function",$t=Array.isArray,Kt=s=>$t(s)||typeof s?.[Symbol.iterator]=="function",mt=`[ 	
\f\r]`,L=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Bt=/-->/g,Ft=/>/g,S=RegExp(`>|${mt}(?:([^\\s"'>=/]+)(${mt}*=${mt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Gt=/'/g,jt=/"/g,Vt=/^(?:script|style|textarea|title)$/i,yt=s=>(t,...e)=>({_$litType$:s,strings:t,values:e}),u=yt(1),Be=yt(2),Fe=yt(3),$=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),qt=new WeakMap,E=C.createTreeWalker(C,129);function Zt(s,t){if(!$t(s)||!s.hasOwnProperty("raw"))throw Error("invalid template strings array");return It!==void 0?It.createHTML(t):t}var Yt=(s,t)=>{let e=s.length-1,r=[],n,i=t===2?"<svg>":t===3?"<math>":"",o=L;for(let d=0;d<e;d++){let a=s[d],c,p,h=-1,f=0;for(;f<a.length&&(o.lastIndex=f,p=o.exec(a),p!==null);)f=o.lastIndex,o===L?p[1]==="!--"?o=Bt:p[1]!==void 0?o=Ft:p[2]!==void 0?(Vt.test(p[2])&&(n=RegExp("</"+p[2],"g")),o=S):p[3]!==void 0&&(o=S):o===S?p[0]===">"?(o=n??L,h=-1):p[1]===void 0?h=-2:(h=o.lastIndex-p[2].length,c=p[1],o=p[3]===void 0?S:p[3]==='"'?jt:Gt):o===jt||o===Gt?o=S:o===Bt||o===Ft?o=L:(o=S,n=void 0);let m=o===S&&s[d+1].startsWith("/>")?" ":"";i+=o===L?a+fe:h>=0?(r.push(c),a.slice(0,h)+_t+a.slice(h)+b+m):a+b+(h===-2?d:m)}return[Zt(s,i+(s[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),r]},B=class s{constructor({strings:t,_$litType$:e},r){let n;this.parts=[];let i=0,o=0,d=t.length-1,a=this.parts,[c,p]=Yt(t,e);if(this.el=s.createElement(c,r),E.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(n=E.nextNode())!==null&&a.length<d;){if(n.nodeType===1){if(n.hasAttributes())for(let h of n.getAttributeNames())if(h.endsWith(_t)){let f=p[o++],m=n.getAttribute(h).split(b),g=/([.?@])?(.*)/.exec(f);a.push({type:1,index:i,name:g[2],strings:m,ctor:g[1]==="."?W:g[1]==="?"?Q:g[1]==="@"?X:T}),n.removeAttribute(h)}else h.startsWith(b)&&(a.push({type:6,index:i}),n.removeAttribute(h));if(Vt.test(n.tagName)){let h=n.textContent.split(b),f=h.length-1;if(f>0){n.textContent=Z?Z.emptyScript:"";for(let m=0;m<f;m++)n.append(h[m],H()),E.nextNode(),a.push({type:2,index:++i});n.append(h[f],H())}}}else if(n.nodeType===8)if(n.data===ft)a.push({type:2,index:i});else{let h=-1;for(;(h=n.data.indexOf(b,h+1))!==-1;)a.push({type:7,index:i}),h+=b.length-1}i++}}static createElement(t,e){let r=C.createElement("template");return r.innerHTML=t,r}};function k(s,t,e=s,r){if(t===$)return t;let n=r!==void 0?e._$Co?.[r]:e._$Cl,i=I(t)?void 0:t._$litDirective$;return n?.constructor!==i&&(n?._$AO?.(!1),i===void 0?n=void 0:(n=new i(s),n._$AT(s,e,r)),r!==void 0?(e._$Co??=[])[r]=n:e._$Cl=n),n!==void 0&&(t=k(s,n._$AS(s,t.values),n,r)),t}var Y=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:r}=this._$AD,n=(t?.creationScope??C).importNode(e,!0);E.currentNode=n;let i=E.nextNode(),o=0,d=0,a=r[0];for(;a!==void 0;){if(o===a.index){let c;a.type===2?c=new D(i,i.nextSibling,this,t):a.type===1?c=new a.ctor(i,a.name,a.strings,this,t):a.type===6&&(c=new J(i,this,t)),this._$AV.push(c),a=r[++d]}o!==a?.index&&(i=E.nextNode(),o++)}return E.currentNode=C,n}p(t){let e=0;for(let r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(t,r,e),e+=r.strings.length-2):r._$AI(t[e])),e++}},D=class s{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,r,n){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=r,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=k(this,t,e),I(t)?t===l||t==null||t===""?(this._$AH!==l&&this._$AR(),this._$AH=l):t!==this._$AH&&t!==$&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Kt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==l&&I(this._$AH)?this._$AA.nextSibling.data=t:this.T(C.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:r}=t,n=typeof r=="number"?this._$AC(t):(r.el===void 0&&(r.el=B.createElement(Zt(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===n)this._$AH.p(e);else{let i=new Y(n,this),o=i.u(this.options);i.p(e),this.T(o),this._$AH=i}}_$AC(t){let e=qt.get(t.strings);return e===void 0&&qt.set(t.strings,e=new B(t)),e}k(t){$t(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,r,n=0;for(let i of t)n===e.length?e.push(r=new s(this.O(H()),this.O(H()),this,this.options)):r=e[n],r._$AI(i),n++;n<e.length&&(this._$AR(r&&r._$AB.nextSibling,n),e.length=n)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let r=Ht(t).nextSibling;Ht(t).remove(),t=r}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},T=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,r,n,i){this.type=1,this._$AH=l,this._$AN=void 0,this.element=t,this.name=e,this._$AM=n,this.options=i,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=l}_$AI(t,e=this,r,n){let i=this.strings,o=!1;if(i===void 0)t=k(this,t,e,0),o=!I(t)||t!==this._$AH&&t!==$,o&&(this._$AH=t);else{let d=t,a,c;for(t=i[0],a=0;a<i.length-1;a++)c=k(this,d[r+a],e,a),c===$&&(c=this._$AH[a]),o||=!I(c)||c!==this._$AH[a],c===l?t=l:t!==l&&(t+=(c??"")+i[a+1]),this._$AH[a]=c}o&&!n&&this.j(t)}j(t){t===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},W=class extends T{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===l?void 0:t}},Q=class extends T{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==l)}},X=class extends T{constructor(t,e,r,n,i){super(t,e,r,n,i),this.type=5}_$AI(t,e=this){if((t=k(this,t,e,0)??l)===$)return;let r=this._$AH,n=t===l&&r!==l||t.capture!==r.capture||t.once!==r.once||t.passive!==r.passive,i=t!==l&&(r===l||n);n&&this.element.removeEventListener(this.name,this,r),i&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},J=class{constructor(t,e,r){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(t){k(this,t)}},Wt={M:_t,P:b,A:ft,C:1,L:Yt,R:Y,D:Kt,V:k,I:D,H:T,N:Q,U:X,B:W,F:J},$e=gt.litHtmlPolyfillSupport;$e?.(B,D),(gt.litHtmlVersions??=[]).push("3.3.3");var Qt=(s,t,e)=>{let r=e?.renderBefore??t,n=r._$litPart$;if(n===void 0){let i=e?.renderBefore??null;r._$litPart$=n=new D(t.insertBefore(H(),i),i,void 0,e??{})}return n._$AI(s),n};var vt=globalThis,A=class extends v{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Qt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return $}};A._$litElement$=!0,A.finalized=!0,vt.litElementHydrateSupport?.({LitElement:A});var ye=vt.litElementPolyfillSupport;ye?.({LitElement:A});(vt.litElementVersions??=[]).push("4.2.2");var P={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Xt=s=>(...t)=>({_$litDirective$:s,values:t}),tt=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,r){this._$Ct=t,this._$AM=e,this._$Ci=r}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var{I:sr}=Wt;var Jt=s=>s.strings===void 0;var ve={},te=(s,t=ve)=>s._$AH=t;var et=Xt(class extends tt{constructor(s){if(super(s),s.type!==P.PROPERTY&&s.type!==P.ATTRIBUTE&&s.type!==P.BOOLEAN_ATTRIBUTE)throw Error("The `live` directive is not allowed on child or event bindings");if(!Jt(s))throw Error("`live` bindings can only contain a single expression")}render(s){return s}update(s,[t]){if(t===$||t===l)return t;let e=s.element,r=s.name;if(s.type===P.PROPERTY){if(t===e[r])return $}else if(s.type===P.BOOLEAN_ATTRIBUTE){if(!!t===e.hasAttribute(r))return $}else if(s.type===P.ATTRIBUTE&&e.getAttribute(r)===t+"")return $;return te(s),t}});var G=["today","yesterday","this_week","last_week","this_month","last_month","this_quarter","this_year","now-7d","now-30d","now-12m"];function y(s){let t=/^(\d{4})-(\d{2})-(\d{2})$/.exec(s);if(!t)throw new Error(`invalid date: ${s}`);let[,e,r,n]=t;return new Date(Date.UTC(Number(e),Number(r)-1,Number(n)))}function rt(s){return s.toISOString().slice(0,10)}function wt(s){try{return rt(y(s))===s}catch{return!1}}function _(s,t){return rt(new Date(y(s).getTime()+t*864e5))}function M(s,t=0){let e=y(s);return rt(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t,1)))}function R(s,t=0){let e=y(s);return rt(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t+1,0)))}function bt(s){let t=(y(s).getUTCDay()+6)%7;return _(s,-t)}function j(s){return Math.round((y(s.end).getTime()-y(s.start).getTime())/864e5)+1}function At(s){let t=y(s.start);if(t.getUTCDate()!==1||R(s.end)!==s.end)return null;let e=y(s.end);return(e.getUTCFullYear()-t.getUTCFullYear())*12+(e.getUTCMonth()-t.getUTCMonth())+1}function st(s,t=new Date){let e={year:"numeric",month:"2-digit",day:"2-digit"},r;try{r=new Intl.DateTimeFormat("en-CA",{...e,timeZone:s}).formatToParts(t)}catch{r=new Intl.DateTimeFormat("en-CA",e).formatToParts(t)}let n=i=>r.find(o=>o.type===i)?.value??"";return`${n("year")}-${n("month")}-${n("day")}`}function w(s,t){switch(s){case"today":return{start:t,end:t};case"yesterday":{let e=_(t,-1);return{start:e,end:e}}case"this_week":{let e=bt(t);return{start:e,end:_(e,6)}}case"last_week":{let e=_(bt(t),-7);return{start:e,end:_(e,6)}}case"this_month":return{start:M(t),end:R(t)};case"last_month":return{start:M(t,-1),end:R(t,-1)};case"this_quarter":{let e=y(t).getUTCMonth(),r=M(t,-(e%3));return{start:r,end:R(r,2)}}case"this_year":{let e=t.slice(0,4);return{start:`${e}-01-01`,end:`${e}-12-31`}}case"now-7d":return{start:_(t,-6),end:t};case"now-30d":return{start:_(t,-29),end:t};case"now-12m":return{start:M(t,-11),end:R(t)}}}function xt(s){let t=At(s);if(t!==null){let r=y(s.start).getUTCMonth();return t===1?"month":t===3&&r%3===0?"quarter":t===12&&r===0?"year":"months"}let e=j(s);return e===1?"day":e===7&&bt(s.start)===s.start?"week":"days"}function St(s,t){let e=At(s);if(e!==null){let n=e*t;return{start:M(s.start,n),end:R(s.end,n)}}let r=j(s)*t;return{start:_(s.start,r),end:_(s.end,r)}}function ee(s,t){switch(xt(s)){case"day":return w("today",t);case"week":return w("this_week",t);case"month":return w("this_month",t);case"quarter":return w("this_quarter",t);case"year":return w("this_year",t);case"months":{let r=At(s)??1;return{start:M(t,-(r-1)),end:R(t)}}case"days":return{start:_(t,-(j(s)-1)),end:t}}}function nt(s,t){return s.start<=t&&t<=s.end}function F(s){return _(s.end,1)}function N(s,t,e=new Date){let r=st(t,e);if(!nt(s,r))return F(s);let n;try{n=new Intl.DateTimeFormat("en-GB",{timeZone:t,hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(e)}catch{return F(s)}let i=Number(n.find(c=>c.type==="hour")?.value),o=Number(n.find(c=>c.type==="minute")?.value);if(!Number.isFinite(i)||o!==e.getUTCMinutes())return F(s);let d=s.start===r?Math.max(i,1):i,a=be(t,e,d-i);return`${r}T${String(d).padStart(2,"0")}:00:00${a}`}function be(s,t,e){let r=new Date(t.getTime()+e*36e5),n=new Intl.DateTimeFormat("en-US",{timeZone:s,timeZoneName:"longOffset"}).formatToParts(r).find(o=>o.type==="timeZoneName")?.value??"GMT",i=/^GMT([+-]\d{2}):?(\d{2})?$/.exec(n);return i?`${i[1]}:${i[2]??"00"}`:"+00:00"}var we=31;function re(s){let t=j(s);return t<=2?"hour":t<=45?"day":t<=120?"week":"month"}function it(s,t){return s!=="hour"||j(t)<=we}var se={title:"Energy cost",previous:"Previous",next:"Next",now:"Now",refresh:"Refresh",period:"Period",custom:"Custom period",from:"From",to:"To",apply:"Apply",grouping:"Grouping","grouping.auto":"Auto","grouping.hour":"Hours","grouping.day":"Days","grouping.week":"Weeks","grouping.month":"Months","grouping.hour_too_long":"Hours: up to 31 days","preset.today":"Today","preset.yesterday":"Yesterday","preset.this_week":"This week","preset.last_week":"Last week","preset.this_month":"This month","preset.last_month":"Last month","preset.this_quarter":"This quarter","preset.this_year":"This year","preset.now-7d":"Last 7 days","preset.now-30d":"Last 30 days","preset.now-12m":"Last 12 months",device:"Device",total:"Total",kwh:"kWh",cost:"Cost",avg_price:"Avg. price",breakdown:"By period",breakdown_device:"Show",all_devices:"All devices",data_quality:"Data quality",loading:"Loading…",no_devices:"No energy sensors selected. Add them in the integration options.",no_plan:"No tariff plan covers this period: costs are unknown.",unpriced:"{hours} h before the first tariff plan are not priced.","status.complete":"Complete","status.estimated":"Contains estimated hours (spread over a data gap)","status.partial":"Some hours are missing","status.missing":"No data","issue.estimated":"estimated","issue.excluded_negative":"excluded (negative)","issue.excluded_spike":"excluded (spike)","statistics.no_statistics":"no statistics yet","statistics.unsupported":"unsupported sensor","error.not_loaded":"Energy Cost Stats is not set up or not loaded.","error.invalid_period":"Invalid period.","error.period_too_long":"The period is too long for this grouping.","error.unknown_entity":"The card lists a sensor that is not selected in the integration.","error.unknown_command":"The integration is not loaded (restart Home Assistant after installing).","error.generic":"Could not load the report: {message}",coverage:"{measured} measured, {estimated} estimated, {excluded} excluded, {missing} missing of {expected} h","compare.title":"Tariff comparison","compare.tariff":"Tariff","compare.zones":"Consumption by zone","compare.difference":"Difference","compare.current":"Current tariff","compare.best":"best","compare.actual_incomplete":"The current tariff does not cover the whole period, so its cost and the differences are incomplete.","error.invalid_scenario":"Invalid tariff scenario in the card config: {message}","preset.single_rate":"Single-rate","preset.ru_two_zone":"Two-zone","preset.ru_three_zone":"Three-zone","zone.t0":"Single","zone.t1":"Day","zone.t1.peak":"Peak","zone.t2":"Night","zone.t3":"Semi-peak"},Ae={title:"Стоимость электроэнергии",previous:"Назад",next:"Вперёд",now:"Сейчас",refresh:"Обновить",period:"Период",custom:"Свой период",from:"С",to:"По",apply:"Применить",grouping:"Группировка","grouping.auto":"Авто","grouping.hour":"По часам","grouping.day":"По дням","grouping.week":"По неделям","grouping.month":"По месяцам","grouping.hour_too_long":"По часам: до 31 дня","preset.today":"Сегодня","preset.yesterday":"Вчера","preset.this_week":"Эта неделя","preset.last_week":"Прошлая неделя","preset.this_month":"Этот месяц","preset.last_month":"Прошлый месяц","preset.this_quarter":"Этот квартал","preset.this_year":"Этот год","preset.now-7d":"Последние 7 дней","preset.now-30d":"Последние 30 дней","preset.now-12m":"Последние 12 месяцев",device:"Устройство",total:"Итого",kwh:"кВт·ч",cost:"Сумма",avg_price:"Ср. цена",breakdown:"По периодам",breakdown_device:"Показать",all_devices:"Все устройства",data_quality:"Качество данных",loading:"Загрузка…",no_devices:"Не выбраны датчики энергии. Добавьте их в настройках интеграции.",no_plan:"Для этого периода нет тарифного плана: стоимость неизвестна.",unpriced:"{hours} ч до первого тарифного плана не оценены.","status.complete":"Полные данные","status.estimated":"Есть оценочные часы (распределены по пропуску)","status.partial":"Часть часов отсутствует","status.missing":"Нет данных","issue.estimated":"оценка","issue.excluded_negative":"исключено (отрицательное)","issue.excluded_spike":"исключено (выброс)","statistics.no_statistics":"статистики пока нет","statistics.unsupported":"датчик не поддерживается","error.not_loaded":"Energy Cost Stats не настроена или не загружена.","error.invalid_period":"Неверный период.","error.period_too_long":"Период слишком длинный для этой группировки.","error.unknown_entity":"В карточке указан датчик, не выбранный в интеграции.","error.unknown_command":"Интеграция не загружена (перезапустите Home Assistant после установки).","error.generic":"Не удалось загрузить отчёт: {message}",coverage:"{measured} измерено, {estimated} оценено, {excluded} исключено, {missing} нет из {expected} ч","compare.title":"Сравнение тарифов","compare.tariff":"Тариф","compare.zones":"Потребление по зонам","compare.difference":"Разница","compare.current":"Текущий тариф","compare.best":"выгоднее","compare.actual_incomplete":"Текущий тариф покрывает не весь период: его сумма и разница неполные.","error.invalid_scenario":"Ошибка в сценарии тарифа в настройках карточки: {message}","preset.single_rate":"Однозонный","preset.ru_two_zone":"Двухзонный","preset.ru_three_zone":"Трёхзонный","zone.t0":"Круглосуточно","zone.t1":"День","zone.t1.peak":"Пик","zone.t2":"Ночь","zone.t3":"Полупик"},ot=class{constructor(t){this.locale=t||"en",this.table=this.locale.toLowerCase().startsWith("ru")?Ae:se}t(t,e={}){return this.table[t].replace(/\{(\w+)\}/g,(r,n)=>n in e?String(e[n]):`{${n}}`)}preset(t){return this.t(`preset.${t}`)}grouping(t){return this.t(`grouping.${t}`)}number(t,e){return t==null?"—":new Intl.NumberFormat(this.locale,{minimumFractionDigits:e,maximumFractionDigits:e}).format(Number(t))}money(t,e){if(t==null)return"—";if(e)try{return new Intl.NumberFormat(this.locale,{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(t))}catch{}return this.number(t,2)}presetName(t){let e=`preset.${t}`;return e in se?this.t(e):t}zoneName(t,e){if(t==="t1"&&e>=3)return this.t("zone.t1.peak");let n={t0:"zone.t0",t1:"zone.t1",t2:"zone.t2",t3:"zone.t3"}[t];return n?this.t(n):t}signedMoney(t,e,r){let n=Math.round(t*100)/100,i=n>0?"+":n<0?"−":"±",o=this.money(Math.abs(n).toFixed(2),e);if(!r)return`${i}${o}`;let d=new Intl.NumberFormat(this.locale,{maximumFractionDigits:1}).format(Math.abs(n/r*100));return`${i}${o} (${i}${d} %)`}avgPrice(t,e){return t===null||e===null||Number(e)===0?"—":this.number(String(Number(t)/Number(e)),2)}date(t,e){return new Intl.DateTimeFormat(this.locale,{...e,timeZone:"UTC"}).format(new Date(`${t}T00:00:00Z`))}periodLabel(t){switch(xt(t)){case"day":return this.date(t.start,{day:"numeric",month:"long",year:"numeric"});case"month":return this.date(t.start,{month:"long",year:"numeric"});case"quarter":return`Q${Math.floor(Number(t.start.slice(5,7))/3)+1} ${t.start.slice(0,4)}`;case"year":return t.start.slice(0,4);case"months":return`${this.date(t.start,{month:"short",year:"numeric"})} – ${this.date(t.end,{month:"short",year:"numeric"})}`;default:{let r=t.start.slice(0,4)===t.end.slice(0,4),n=this.date(t.start,{day:"numeric",month:"short",...r?{}:{year:"numeric"}}),i=this.date(t.end,{day:"numeric",month:"short",year:"numeric"});return`${n} – ${i}`}}}bucketLabel(t,e){let r=t.slice(0,10);switch(e){case"hour":return`${this.date(r,{day:"numeric",month:"short"})} ${t.slice(11,16)}`;case"day":return this.date(r,{weekday:"short",day:"numeric",month:"short"});case"week":return this.date(r,{day:"numeric",month:"short",year:"numeric"});case"month":return this.date(r,{month:"long",year:"numeric"});default:return this.t("total")}}};var xe="energy_cost_stats/report",Se="energy_cost_stats/compare",Et=["single_rate","ru_two_zone","ru_three_zone"],Ct=5;function Ee(s){let t={type:xe,start:s.period.start,end:s.end??N(s.period,s.timeZone,s.now),grouping:s.grouping};return s.entities&&s.entities.length>0&&(t.entities=s.entities),t}function ne(s,t){return s.callWS(Ee(t))}function kt(s){if(s&&typeof s=="object"&&"code"in s){let t=s.code;return typeof t=="string"?t:void 0}}function at(s){return s&&typeof s=="object"&&"message"in s?String(s.message):String(s)}function Ce(s){let t={preset:s.preset,prices:Object.fromEntries(Object.entries(s.prices).map(([e,r])=>[e,String(r)]))};return s.name&&(t.name=s.name),s.periods&&(t.periods=s.periods),t}function ke(s){let t={type:Se,start:s.period.start,end:s.end??N(s.period,s.timeZone,s.now),scenarios:s.scenarios.map(Ce)};return s.entities&&s.entities.length>0&&(t.entities=s.entities),t}function ie(s,t){return s.callWS(ke(t))}var x="energy-cost-stats-card",oe=["auto","hour","day","week","month"],Te=600*1e3,Pe="M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",Re="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",De="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";function Tt(s){return u`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${s}></path></svg>`}var ct=class extends A{constructor(){super(...arguments);this._groupingChoice="auto";this._loading=!1;this._customOpen=!1;this._customStart="";this._customEnd="";this._breakdownEntity="";this._requestSeq=0;this._comparisonSeq=0;this._lastRequestOpen=!1}static{this.properties={hass:{attribute:!1},_config:{state:!0},_period:{state:!0},_groupingChoice:{state:!0},_report:{state:!0},_error:{state:!0},_loading:{state:!0},_customOpen:{state:!0},_customStart:{state:!0},_customEnd:{state:!0},_breakdownEntity:{state:!0},_comparison:{state:!0},_comparisonError:{state:!0}}}static getStubConfig(){return{type:`custom:${x}`,period:"this_month"}}setConfig(e){if(!e||typeof e!="object")throw new Error("Invalid configuration");if(e.period!==void 0&&!G.includes(e.period))throw new Error(`Unknown period: ${String(e.period)}`);if(e.grouping!==void 0&&!oe.includes(e.grouping))throw new Error(`Unknown grouping: ${String(e.grouping)}`);if(e.entities!==void 0&&(!Array.isArray(e.entities)||e.entities.some(n=>typeof n!="string")))throw new Error("entities must be a list of entity ids");if(e.compare!==void 0){if(!Array.isArray(e.compare)||e.compare.length<1||e.compare.length>Ct)throw new Error(`compare must be a list of 1 to ${Ct} tariff scenarios`);for(let n of e.compare)if(!n||typeof n!="object"||!Et.includes(n.preset)||!n.prices||typeof n.prices!="object")throw new Error(`each compare entry needs a preset (${Et.join(", ")}) and prices`)}let r=this._config;this._config=e,this._groupingChoice=e.grouping??"auto",r&&this._period&&(this._period=void 0,this._report=void 0,this._comparison=void 0)}getCardSize(){return 3+(this._report?.devices.length??2)}get _strings(){return new ot(this.hass?.locale?.language??this.hass?.language)}get _timeZone(){return this._reportTimeZone??this.hass?.config?.time_zone}_today(){return st(this._timeZone)}get grouping(){let e=this._period;if(!e)return"day";let r=this._groupingChoice;return r!=="auto"&&it(r,e)?r:re(e)}connectedCallback(){super.connectedCallback(),this._timer=setInterval(()=>{this._period&&this._lastRequestOpen&&!this._loading&&this._load(!0)},Te)}disconnectedCallback(){super.disconnectedCallback(),this._timer!==void 0&&clearInterval(this._timer),this._timer=void 0}willUpdate(e){this.hass&&this._config&&!this._period&&(this._period=w(this._config.period??"this_month",this._today())),super.willUpdate(e)}updated(e){super.updated(e),!(!this.hass||!this._period)&&(e.has("_period")||e.has("_groupingChoice")||e.has("hass")&&e.get("hass")===void 0)&&this._load()}async _load(e=!1){let r=this.hass,n=this._period;if(!r||!n)return;let i=++this._requestSeq,o=this._timeZone,d=N(n,o);this._loading=!0;try{let a=await ne(r,{period:n,grouping:this.grouping,entities:this._config?.entities,timeZone:o,end:d});if(i!==this._requestSeq)return;if(this._report=a,this._error=void 0,this._reportTimeZone=a.time_zone,this._lastRequestOpen=N(n,a.time_zone)!==F(n),a.time_zone!==o&&nt(n,st(a.time_zone)))this._load(e);else if(this._config?.compare){let c=JSON.stringify([n,this._config.entities??[]]);c!==this._comparisonKey?(this._comparison=void 0,this._comparisonError=void 0,this._comparisonKey=c,this._loadComparison(n,d)):e&&this._loadComparison(n,d)}}catch(a){if(i!==this._requestSeq)return;let c=kt(a),h=c?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_command:"error.unknown_command"}[c]:void 0;this._error=h?this._strings.t(h):this._strings.t("error.generic",{message:at(a)}),this._report=void 0}finally{i===this._requestSeq&&(this._loading=!1)}}async _loadComparison(e,r){let n=this.hass,i=this._config?.compare;if(!n||!i)return;let o=++this._comparisonSeq;try{let d=await ie(n,{period:e,entities:this._config?.entities,end:r,scenarios:i});if(o!==this._comparisonSeq)return;this._comparison=d,this._comparisonError=void 0}catch(d){if(o!==this._comparisonSeq)return;this._comparison=void 0,this._comparisonError=kt(d)==="invalid_scenario"?this._strings.t("error.invalid_scenario",{message:at(d)}):this._strings.t("error.generic",{message:at(d)})}}_selectedPreset(){if(!this._period)return"";let e=this._today(),r=this._period;return G.find(n=>{let i=w(n,e);return i.start===r.start&&i.end===r.end})??""}_onPreset(e){let r=e.target.value;if(r==="custom"){this._openCustom();return}G.includes(r)&&(this._customOpen=!1,this._period=w(r,this._today()))}_openCustom(){this._customOpen=!0,this._customStart=this._period?.start??this._today(),this._customEnd=this._period?.end??this._today()}_applyCustom(){let e=this._customStart,r=this._customEnd;!wt(e)||!wt(r)||(this._period=e<=r?{start:e,end:r}:{start:r,end:e},this._customOpen=!1)}_shift(e){this._period&&(this._period=St(this._period,e))}_now(){this._period&&(this._period=ee(this._period,this._today()))}_onGrouping(e){this._groupingChoice=e.target.value}render(){if(!this._config||!this.hass||!this._period)return l;let e=this._strings,r=this._config.title??e.t("title");return u`
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
    `}_renderPicker(e){let r=this._period,n=this._selectedPreset(),i=this._today(),o=nt(r,i),d=St(r,1).start>i;return u`
      <div class="picker">
        <select
          class="preset"
          aria-label=${e.t("period")}
          .value=${et(n)}
          @change=${this._onPreset}
        >
          <option value="" ?hidden=${n!==""} ?selected=${n===""}>
            ${e.t("custom")}
          </option>
          ${G.map(a=>u`<option value=${a} ?selected=${a===n}>${e.preset(a)}</option>`)}
          <option value="custom">${e.t("custom")}…</option>
        </select>
        <div class="nav">
          <button
            class="icon prev"
            title=${e.t("previous")}
            aria-label=${e.t("previous")}
            @click=${()=>this._shift(-1)}
          >
            ${Tt(Pe)}
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
            ${Tt(Re)}
          </button>
          <button class="text now" ?disabled=${o} @click=${this._now}>
            ${e.t("now")}
          </button>
        </div>
        <button
          class="icon refresh"
          title=${e.t("refresh")}
          aria-label=${e.t("refresh")}
          @click=${()=>{this._load(!0)}}
        >
          ${Tt(De)}
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
    `}_renderReport(e,r){if(r.devices.length===0)return u`<div class="note">${e.t("no_devices")}</div>`;let n=new Map(r.devices.map(d=>[d.entity_id,d])),i=r.totals,o=r.plans.length===0;return u`
      ${o?u`<div class="note warning">${e.t("no_plan")}</div>`:l}
      ${!o&&r.unpriced_hours>0?u`<div class="note warning">
            ${e.t("unpriced",{hours:r.unpriced_hours})}
          </div>`:l}
      <div class="table-wrap">
        <table class="devices">
          ${this._renderHead(e,r,e.t("device"),i)}
          <tbody>
            ${i.rows.map(d=>{let a=d.entity_id?n.get(d.entity_id):void 0,c=a?.name??d.entity_id??"",p=a&&a.statistics!=="ok"?e.t(`statistics.${a.statistics}`):"";return this._renderRow(e,r,d,c,p)})}
          </tbody>
          <tfoot>
            ${this._renderRow(e,r,i.total,e.t("total"),"")}
          </tfoot>
        </table>
      </div>
      ${this._config?.compare?this._renderComparison(e,r):l}
      ${r.grouping!=="total"?this._renderBreakdown(e,r):l}
      ${r.issues.length>0?this._renderIssues(e,r,n):l}
    `}_renderHead(e,r,n,i){let o=r.currency;return u`
      <thead>
        <tr>
          <th rowspan="2" class="name">${n}</th>
          ${r.zones.map((d,a)=>{let c=i.total.zones[a]?.price??null;return u`<th colspan="2" class="zone">
              ${d.name}${c!==null?u`<span class="price">${e.money(c,o)}</span>`:l}
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
    `}_renderRow(e,r,n,i,o){let d=r.currency,a=n.coverage,c=e.t("coverage",{measured:a.measured,estimated:a.estimated,excluded:a.excluded,missing:a.missing,expected:a.expected});return u`
      <tr class="status-${n.status}">
        <th scope="row" class="name">
          <span>${i}</span>
          ${n.status!=="complete"?u`<span
                class="badge ${n.status}"
                title="${e.t(`status.${n.status}`)} · ${c}"
                >${n.status==="estimated"?"≈":"!"}</span
              >`:l}
          ${o?u`<span class="sub">${o}</span>`:l}
        </th>
        ${n.zones.map(p=>u`<td class="num">${e.number(p.kwh,2)}</td>
              <td class="num">${e.money(p.cost,d)}</td>`)}
        <td class="num strong">${e.number(n.kwh,2)}</td>
        <td class="num strong">${e.money(n.cost,d)}</td>
        <td class="num">${e.avgPrice(n.cost,n.kwh)}</td>
      </tr>
    `}_renderBreakdown(e,r){let n=this._breakdownEntity,i=n?r.devices.findIndex(c=>c.entity_id===n):-1,o=c=>(i>=0?c.rows.find(p=>p.entity_id===n):void 0)??c.total,d=this._groupingChoice,a=d==="auto"||it(d,this._period)?d:"auto";return u`
      <details class="breakdown" ?open=${this._config?.show_breakdown??!1}>
        <summary>${e.t("breakdown")}</summary>
        <div class="breakdown-controls">
          <label
            >${e.t("breakdown_device")}
            <select
              class="breakdown-device"
              .value=${et(i>=0?n:"")}
              @change=${c=>{this._breakdownEntity=c.target.value}}
            >
              <option value="">${e.t("all_devices")}</option>
              ${r.devices.map(c=>u`<option value=${c.entity_id} ?selected=${c.entity_id===n}>
                    ${c.name}
                  </option>`)}
            </select>
          </label>
          <label
            >${e.t("grouping")}
            <select class="grouping" .value=${et(a)} @change=${this._onGrouping}>
              ${oe.map(c=>{let p=c==="auto"||it(c,this._period);return u`<option
                  value=${c}
                  ?disabled=${!p}
                  ?selected=${c===a}
                >
                  ${p?e.grouping(c):e.t("grouping.hour_too_long")}
                </option>`})}
            </select>
          </label>
        </div>
        <div class="table-wrap">
          <table class="buckets">
            ${this._renderHead(e,r,e.t("period"),r.totals)}
            <tbody>
              ${r.buckets.map(c=>this._renderRow(e,r,o(c),this._bucketLabel(e,r,c),""))}
            </tbody>
            <tfoot>
              ${this._renderRow(e,r,o(r.totals),e.t("total"),"")}
            </tfoot>
          </table>
        </div>
      </details>
    `}_renderComparison(e,r){let n=this._comparison,i=r.currency,o;if(this._comparisonError)o=u`<div class="error" role="alert">${this._comparisonError}</div>`;else if(!n)o=u`<div class="note">${e.t("loading")}</div>`;else{let d=n.actual.totals.total,a=d.cost!==null&&n.actual.unpriced_hours===0&&n.actual.plans.length>0,c=[{name:e.t("compare.current"),sub:n.actual.plans.map(m=>m.name).join(", "),doc:n.actual,current:!0},...n.scenarios.map((m,g)=>({name:this._config?.compare?.[g]?.name??e.presetName(m.preset),sub:"",doc:m.report,current:!1}))],p=c.filter(m=>!m.current||a).map(m=>m.doc.totals.total.cost).filter(m=>m!==null).map(Number),h=p.length>1?Math.min(...p):null,f=h!==null&&p.filter(m=>m===h).length===1?h:null;o=u`
        <div class="table-wrap">
          <table class="compare">
            <thead>
              <tr>
                <th class="name">${e.t("compare.tariff")}</th>
                <th class="name zones">${e.t("compare.zones")}</th>
                <th class="num">${e.t("cost")}</th>
                <th class="num">${e.t("avg_price")}</th>
                <th class="num">${e.t("compare.difference")}</th>
              </tr>
            </thead>
            <tbody>
              ${c.map(m=>{let g=m.doc.totals.total,Rt=f!==null&&g.cost!==null&&Number(g.cost)===f&&(!m.current||a),O=m.current||!a||g.cost===null?null:Number(g.cost)-Number(d.cost),ae=m.doc.zones.flatMap((dt,Oe)=>{let Dt=g.zones.find(ce=>ce.key===dt.key)?.kwh??null;return Dt===null?[]:[`${m.current?dt.name:e.zoneName(dt.key,m.doc.zones.length)} ${e.number(Dt,1)}`]}).join(" · ");return u`<tr class=${Rt?"best":""}>
                  <th scope="row" class="name">
                    <span>${m.name}</span>
                    ${Rt?u`<span class="badge best">${e.t("compare.best")}</span>`:l}
                    ${m.sub?u`<span class="sub">${m.sub}</span>`:l}
                  </th>
                  <td class="name zones">${ae} ${e.t("kwh")}</td>
                  <td class="num strong">${e.money(g.cost,i)}</td>
                  <td class="num">${e.avgPrice(g.cost,g.kwh)}</td>
                  <td class="num diff ${O===null?"":O<0?"cheaper":O>0?"dearer":""}">
                    ${O===null?"—":e.signedMoney(O,i,Number(d.cost))}
                  </td>
                </tr>`})}
            </tbody>
          </table>
        </div>
        ${a?l:u`<div class="note warning">${e.t("compare.actual_incomplete")}</div>`}
      `}return u`
      <details class="comparison" open>
        <summary>${e.t("compare.title")}</summary>
        ${o}
      </details>
    `}_bucketLabel(e,r,n){if(r.grouping==="week"){let i=n.start.slice(0,10);return e.periodLabel({start:i,end:_(i,6)})}return e.bucketLabel(n.start,r.grouping)}_renderIssues(e,r,n){return u`
      <details class="issues">
        <summary>${e.t("data_quality")} (${r.issues.length})</summary>
        <ul>
          ${r.issues.map(i=>u`<li>
                <span class="who">${n.get(i.entity_id)?.name??i.entity_id}</span>:
                ${e.t(`issue.${i.kind}`)},
                ${e.bucketLabel(i.start,"hour")} – ${e.bucketLabel(i.end,"hour")}
                (${i.hours} h, ${e.number(i.kwh,3)} ${e.t("kwh")})
              </li>`)}
        </ul>
      </details>
    `}static{this.styles=ut`
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
    .compare td.zones {
      white-space: normal;
      color: var(--secondary-text-color);
      font-size: 0.85em;
      min-width: 12em;
    }
    .compare tr.best th.name span:first-child {
      font-weight: 600;
    }
    .badge.best {
      background: var(--success-color, #43a047);
      padding: 0 6px;
      cursor: default;
    }
    .diff.cheaper {
      color: var(--success-color, #43a047);
    }
    .diff.dearer {
      color: var(--error-color, #db4437);
    }
    .issues ul {
      margin: 4px 0;
      padding-inline-start: 20px;
      color: var(--secondary-text-color);
    }
  `}};var Me=3e4;function Pt(){let s=window.customElements;s.get(x)||(s.define(x,ct),window.customCards=window.customCards??[],window.customCards.some(t=>t.type===x)||window.customCards.push({type:x,name:"Energy Cost Stats",description:"Electricity cost per device, split by tariff zones",preview:!1}))}function Ne(){document.querySelector("home-assistant")!==null&&!window.customElements.get("home-assistant")?(window.customElements.whenDefined("home-assistant").then(Pt),setTimeout(()=>{window.customElements.get(x)||(console.warn(`${x}: the frontend did not boot in time; defining the card anyway`),Pt())},Me)):Pt()}Ne();export{Me as BOOT_TIMEOUT_MS,Pt as defineCard,Ne as registerCard};
