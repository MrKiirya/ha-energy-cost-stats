var G=globalThis,F=G.ShadowRoot&&(G.ShadyCSS===void 0||G.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,at=Symbol(),St=new WeakMap,U=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==at)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(F&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=St.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&St.set(e,t))}return t}toString(){return this.cssText}},Et=r=>new U(typeof r=="string"?r:r+"",void 0,at),dt=(r,...t)=>{let e=r.length===1?r[0]:t.reduce((s,i,n)=>s+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+r[n+1],r[0]);return new U(e,r,at)},Ct=(r,t)=>{if(F)r.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),i=G.litNonce;i!==void 0&&s.setAttribute("nonce",i),s.textContent=e.cssText,r.appendChild(s)}},ct=F?r=>r:r=>r instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return Et(e)})(r):r;var{is:Xt,defineProperty:te,getOwnPropertyDescriptor:ee,getOwnPropertyNames:se,getOwnPropertySymbols:re,getPrototypeOf:ie}=Object,V=globalThis,kt=V.trustedTypes,ne=kt?kt.emptyScript:"",oe=V.reactiveElementPolyfillSupport,M=(r,t)=>r,lt={toAttribute(r,t){switch(t){case Boolean:r=r?ne:null;break;case Object:case Array:r=r==null?r:JSON.stringify(r)}return r},fromAttribute(r,t){let e=r;switch(t){case Boolean:e=r!==null;break;case Number:e=r===null?null:Number(r);break;case Object:case Array:try{e=JSON.parse(r)}catch{e=null}}return e}},Pt=(r,t)=>!Xt(r,t),Tt={attribute:!0,type:String,converter:lt,reflect:!1,useDefault:!1,hasChanged:Pt};Symbol.metadata??=Symbol("metadata"),V.litPropertyMetadata??=new WeakMap;var $=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Tt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),i=this.getPropertyDescriptor(t,s,e);i!==void 0&&te(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){let{get:i,set:n}=ee(this.prototype,t)??{get(){return this[e]},set(o){this[e]=o}};return{get:i,set(o){let c=i?.call(this);n?.call(this,o),this.requestUpdate(t,c,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Tt}static _$Ei(){if(this.hasOwnProperty(M("elementProperties")))return;let t=ie(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(M("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(M("properties"))){let e=this.properties,s=[...se(e),...re(e)];for(let i of s)this.createProperty(i,e[i])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,i]of e)this.elementProperties.set(s,i)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let i=this._$Eu(e,s);i!==void 0&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let i of s)e.unshift(ct(i))}else t!==void 0&&e.push(ct(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return Ct(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(i!==void 0&&s.reflect===!0){let n=(s.converter?.toAttribute!==void 0?s.converter:lt).toAttribute(e,s.type);this._$Em=t,n==null?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,e){let s=this.constructor,i=s._$Eh.get(t);if(i!==void 0&&this._$Em!==i){let n=s.getPropertyOptions(i),o=typeof n.converter=="function"?{fromAttribute:n.converter}:n.converter?.fromAttribute!==void 0?n.converter:lt;this._$Em=i;let c=o.fromAttribute(e,n.type);this[i]=c??this._$Ej?.get(i)??c,this._$Em=null}}requestUpdate(t,e,s,i=!1,n){if(t!==void 0){let o=this.constructor;if(i===!1&&(n=this[t]),s??=o.getPropertyOptions(t),!((s.hasChanged??Pt)(n,e)||s.useDefault&&s.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:n},o){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),n!==!0||o!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),i===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,n]of this._$Ep)this[i]=n;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[i,n]of s){let{wrapped:o}=n,c=this[i];o!==!0||this._$AL.has(i)||c===void 0||this.C(i,void 0,n,c)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[M("elementProperties")]=new Map,$[M("finalized")]=new Map,oe?.({ReactiveElement:$}),(V.reactiveElementVersions??=[]).push("2.1.2");var ht=globalThis,Rt=r=>r,j=ht.trustedTypes,Dt=j?j.createPolicy("lit-html",{createHTML:r=>r}):void 0,pt="$lit$",y=`lit$${Math.random().toFixed(9).slice(2)}$`,gt="?"+y,ae=`<${gt}>`,E=document,L=()=>E.createComment(""),N=r=>r===null||typeof r!="object"&&typeof r!="function",mt=Array.isArray,Ht=r=>mt(r)||typeof r?.[Symbol.iterator]=="function",ut=`[ 	
\f\r]`,O=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Ut=/-->/g,Mt=/>/g,x=RegExp(`>|${ut}(?:([^\\s"'>=/]+)(${ut}*=${ut}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Ot=/'/g,Lt=/"/g,It=/^(?:script|style|textarea|title)$/i,_t=r=>(t,...e)=>({_$litType$:r,strings:t,values:e}),h=_t(1),Ce=_t(2),ke=_t(3),m=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),Nt=new WeakMap,S=E.createTreeWalker(E,129);function Bt(r,t){if(!mt(r)||!r.hasOwnProperty("raw"))throw Error("invalid template strings array");return Dt!==void 0?Dt.createHTML(t):t}var zt=(r,t)=>{let e=r.length-1,s=[],i,n=t===2?"<svg>":t===3?"<math>":"",o=O;for(let c=0;c<e;c++){let a=r[c],d,u,p=-1,f=0;for(;f<a.length&&(o.lastIndex=f,u=o.exec(a),u!==null);)f=o.lastIndex,o===O?u[1]==="!--"?o=Ut:u[1]!==void 0?o=Mt:u[2]!==void 0?(It.test(u[2])&&(i=RegExp("</"+u[2],"g")),o=x):u[3]!==void 0&&(o=x):o===x?u[0]===">"?(o=i??O,p=-1):u[1]===void 0?p=-2:(p=o.lastIndex-u[2].length,d=u[1],o=u[3]===void 0?x:u[3]==='"'?Lt:Ot):o===Lt||o===Ot?o=x:o===Ut||o===Mt?o=O:(o=x,i=void 0);let b=o===x&&r[c+1].startsWith("/>")?" ":"";n+=o===O?a+ae:p>=0?(s.push(d),a.slice(0,p)+pt+a.slice(p)+y+b):a+y+(p===-2?c:b)}return[Bt(r,n+(r[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},H=class r{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let n=0,o=0,c=t.length-1,a=this.parts,[d,u]=zt(t,e);if(this.el=r.createElement(d,s),S.currentNode=this.el.content,e===2||e===3){let p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(i=S.nextNode())!==null&&a.length<c;){if(i.nodeType===1){if(i.hasAttributes())for(let p of i.getAttributeNames())if(p.endsWith(pt)){let f=u[o++],b=i.getAttribute(p).split(y),q=/([.?@])?(.*)/.exec(f);a.push({type:1,index:n,name:q[2],strings:b,ctor:q[1]==="."?Y:q[1]==="?"?Z:q[1]==="@"?W:k}),i.removeAttribute(p)}else p.startsWith(y)&&(a.push({type:6,index:n}),i.removeAttribute(p));if(It.test(i.tagName)){let p=i.textContent.split(y),f=p.length-1;if(f>0){i.textContent=j?j.emptyScript:"";for(let b=0;b<f;b++)i.append(p[b],L()),S.nextNode(),a.push({type:2,index:++n});i.append(p[f],L())}}}else if(i.nodeType===8)if(i.data===gt)a.push({type:2,index:n});else{let p=-1;for(;(p=i.data.indexOf(y,p+1))!==-1;)a.push({type:7,index:n}),p+=y.length-1}n++}}static createElement(t,e){let s=E.createElement("template");return s.innerHTML=t,s}};function C(r,t,e=r,s){if(t===m)return t;let i=s!==void 0?e._$Co?.[s]:e._$Cl,n=N(t)?void 0:t._$litDirective$;return i?.constructor!==n&&(i?._$AO?.(!1),n===void 0?i=void 0:(i=new n(r),i._$AT(r,e,s)),s!==void 0?(e._$Co??=[])[s]=i:e._$Cl=i),i!==void 0&&(t=C(r,i._$AS(r,t.values),i,s)),t}var K=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??E).importNode(e,!0);S.currentNode=i;let n=S.nextNode(),o=0,c=0,a=s[0];for(;a!==void 0;){if(o===a.index){let d;a.type===2?d=new R(n,n.nextSibling,this,t):a.type===1?d=new a.ctor(n,a.name,a.strings,this,t):a.type===6&&(d=new Q(n,this,t)),this._$AV.push(d),a=s[++c]}o!==a?.index&&(n=S.nextNode(),o++)}return S.currentNode=E,i}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},R=class r{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=C(this,t,e),N(t)?t===l||t==null||t===""?(this._$AH!==l&&this._$AR(),this._$AH=l):t!==this._$AH&&t!==m&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Ht(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==l&&N(this._$AH)?this._$AA.nextSibling.data=t:this.T(E.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,i=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=H.createElement(Bt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{let n=new K(i,this),o=n.u(this.options);n.p(e),this.T(o),this._$AH=n}}_$AC(t){let e=Nt.get(t.strings);return e===void 0&&Nt.set(t.strings,e=new H(t)),e}k(t){mt(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,i=0;for(let n of t)i===e.length?e.push(s=new r(this.O(L()),this.O(L()),this,this.options)):s=e[i],s._$AI(n),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=Rt(t).nextSibling;Rt(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},k=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,n){this.type=1,this._$AH=l,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=n,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=l}_$AI(t,e=this,s,i){let n=this.strings,o=!1;if(n===void 0)t=C(this,t,e,0),o=!N(t)||t!==this._$AH&&t!==m,o&&(this._$AH=t);else{let c=t,a,d;for(t=n[0],a=0;a<n.length-1;a++)d=C(this,c[s+a],e,a),d===m&&(d=this._$AH[a]),o||=!N(d)||d!==this._$AH[a],d===l?t=l:t!==l&&(t+=(d??"")+n[a+1]),this._$AH[a]=d}o&&!i&&this.j(t)}j(t){t===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},Y=class extends k{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===l?void 0:t}},Z=class extends k{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==l)}},W=class extends k{constructor(t,e,s,i,n){super(t,e,s,i,n),this.type=5}_$AI(t,e=this){if((t=C(this,t,e,0)??l)===m)return;let s=this._$AH,i=t===l&&s!==l||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,n=t!==l&&(s===l||i);i&&this.element.removeEventListener(this.name,this,s),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},Q=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){C(this,t)}},qt={M:pt,P:y,A:gt,C:1,L:zt,R:K,D:Ht,V:C,I:R,H:k,N:Z,U:W,B:Y,F:Q},de=ht.litHtmlPolyfillSupport;de?.(H,R),(ht.litHtmlVersions??=[]).push("3.3.3");var Gt=(r,t,e)=>{let s=e?.renderBefore??t,i=s._$litPart$;if(i===void 0){let n=e?.renderBefore??null;s._$litPart$=i=new R(t.insertBefore(L(),n),n,void 0,e??{})}return i._$AI(r),i};var ft=globalThis,w=class extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Gt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return m}};w._$litElement$=!0,w.finalized=!0,ft.litElementHydrateSupport?.({LitElement:w});var ce=ft.litElementPolyfillSupport;ce?.({LitElement:w});(ft.litElementVersions??=[]).push("4.2.2");var T={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},Ft=r=>(...t)=>({_$litDirective$:r,values:t}),J=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,s){this._$Ct=t,this._$AM=e,this._$Ci=s}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};var{I:Ge}=qt;var Vt=r=>r.strings===void 0;var le={},jt=(r,t=le)=>r._$AH=t;var X=Ft(class extends J{constructor(r){if(super(r),r.type!==T.PROPERTY&&r.type!==T.ATTRIBUTE&&r.type!==T.BOOLEAN_ATTRIBUTE)throw Error("The `live` directive is not allowed on child or event bindings");if(!Vt(r))throw Error("`live` bindings can only contain a single expression")}render(r){return r}update(r,[t]){if(t===m||t===l)return t;let e=r.element,s=r.name;if(r.type===T.PROPERTY){if(t===e[s])return m}else if(r.type===T.BOOLEAN_ATTRIBUTE){if(!!t===e.hasAttribute(s))return m}else if(r.type===T.ATTRIBUTE&&e.getAttribute(s)===t+"")return m;return jt(r),t}});var B=["today","yesterday","this_week","last_week","this_month","last_month","this_quarter","this_year","now-7d","now-30d","now-12m"];function _(r){let t=/^(\d{4})-(\d{2})-(\d{2})$/.exec(r);if(!t)throw new Error(`invalid date: ${r}`);let[,e,s,i]=t;return new Date(Date.UTC(Number(e),Number(s)-1,Number(i)))}function tt(r){return r.toISOString().slice(0,10)}function yt(r){try{return tt(_(r))===r}catch{return!1}}function g(r,t){return tt(new Date(_(r).getTime()+t*864e5))}function D(r,t=0){let e=_(r);return tt(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t,1)))}function P(r,t=0){let e=_(r);return tt(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t+1,0)))}function $t(r){let t=(_(r).getUTCDay()+6)%7;return g(r,-t)}function z(r){return Math.round((_(r.end).getTime()-_(r.start).getTime())/864e5)+1}function vt(r){let t=_(r.start);if(t.getUTCDate()!==1||P(r.end)!==r.end)return null;let e=_(r.end);return(e.getUTCFullYear()-t.getUTCFullYear())*12+(e.getUTCMonth()-t.getUTCMonth())+1}function et(r,t=new Date){let e={year:"numeric",month:"2-digit",day:"2-digit"},s;try{s=new Intl.DateTimeFormat("en-CA",{...e,timeZone:r}).formatToParts(t)}catch{s=new Intl.DateTimeFormat("en-CA",e).formatToParts(t)}let i=n=>s.find(o=>o.type===n)?.value??"";return`${i("year")}-${i("month")}-${i("day")}`}function v(r,t){switch(r){case"today":return{start:t,end:t};case"yesterday":{let e=g(t,-1);return{start:e,end:e}}case"this_week":{let e=$t(t);return{start:e,end:g(e,6)}}case"last_week":{let e=g($t(t),-7);return{start:e,end:g(e,6)}}case"this_month":return{start:D(t),end:P(t)};case"last_month":return{start:D(t,-1),end:P(t,-1)};case"this_quarter":{let e=_(t).getUTCMonth(),s=D(t,-(e%3));return{start:s,end:P(s,2)}}case"this_year":{let e=t.slice(0,4);return{start:`${e}-01-01`,end:`${e}-12-31`}}case"now-7d":return{start:g(t,-6),end:t};case"now-30d":return{start:g(t,-29),end:t};case"now-12m":return{start:D(t,-11),end:P(t)}}}function bt(r){let t=vt(r);if(t!==null){let s=_(r.start).getUTCMonth();return t===1?"month":t===3&&s%3===0?"quarter":t===12&&s===0?"year":"months"}let e=z(r);return e===1?"day":e===7&&$t(r.start)===r.start?"week":"days"}function wt(r,t){let e=vt(r);if(e!==null){let i=e*t;return{start:D(r.start,i),end:P(r.end,i)}}let s=z(r)*t;return{start:g(r.start,s),end:g(r.end,s)}}function Kt(r,t){switch(bt(r)){case"day":return v("today",t);case"week":return v("this_week",t);case"month":return v("this_month",t);case"quarter":return v("this_quarter",t);case"year":return v("this_year",t);case"months":{let s=vt(r)??1;return{start:D(t,-(s-1)),end:P(t)}}case"days":return{start:g(t,-(z(r)-1)),end:t}}}function st(r,t){return r.start<=t&&t<=r.end}function I(r){return g(r.end,1)}function rt(r,t,e=new Date){let s=et(t,e);if(!st(r,s))return I(r);let i;try{i=new Intl.DateTimeFormat("en-GB",{timeZone:t,hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(e)}catch{return I(r)}let n=Number(i.find(d=>d.type==="hour")?.value),o=Number(i.find(d=>d.type==="minute")?.value);if(!Number.isFinite(n)||o!==e.getUTCMinutes())return I(r);let c=r.start===s?Math.max(n,1):n,a=ue(t,e,c-n);return`${s}T${String(c).padStart(2,"0")}:00:00${a}`}function ue(r,t,e){let s=new Date(t.getTime()+e*36e5),i=new Intl.DateTimeFormat("en-US",{timeZone:r,timeZoneName:"longOffset"}).formatToParts(s).find(o=>o.type==="timeZoneName")?.value??"GMT",n=/^GMT([+-]\d{2}):?(\d{2})?$/.exec(i);return n?`${n[1]}:${n[2]??"00"}`:"+00:00"}var he=31;function Yt(r){let t=z(r);return t<=2?"hour":t<=45?"day":t<=120?"week":"month"}function it(r,t){return r!=="hour"||z(t)<=he}var pe={title:"Energy cost",previous:"Previous",next:"Next",now:"Now",refresh:"Refresh",period:"Period",custom:"Custom period",from:"From",to:"To",apply:"Apply",grouping:"Grouping","grouping.auto":"Auto","grouping.hour":"Hours","grouping.day":"Days","grouping.week":"Weeks","grouping.month":"Months","grouping.hour_too_long":"Hours: up to 31 days","preset.today":"Today","preset.yesterday":"Yesterday","preset.this_week":"This week","preset.last_week":"Last week","preset.this_month":"This month","preset.last_month":"Last month","preset.this_quarter":"This quarter","preset.this_year":"This year","preset.now-7d":"Last 7 days","preset.now-30d":"Last 30 days","preset.now-12m":"Last 12 months",device:"Device",total:"Total",kwh:"kWh",cost:"Cost",avg_price:"Avg. price",breakdown:"By period",breakdown_device:"Show",all_devices:"All devices",data_quality:"Data quality",loading:"Loading…",no_devices:"No energy sensors selected. Add them in the integration options.",no_plan:"No tariff plan covers this period: costs are unknown.",unpriced:"{hours} h before the first tariff plan are not priced.","status.complete":"Complete","status.estimated":"Contains estimated hours (spread over a data gap)","status.partial":"Some hours are missing","status.missing":"No data","issue.estimated":"estimated","issue.excluded_negative":"excluded (negative)","issue.excluded_spike":"excluded (spike)","statistics.no_statistics":"no statistics yet","statistics.unsupported":"unsupported sensor","error.not_loaded":"Energy Cost Stats is not set up or not loaded.","error.invalid_period":"Invalid period.","error.period_too_long":"The period is too long for this grouping.","error.unknown_entity":"The card lists a sensor that is not selected in the integration.","error.unknown_command":"The integration is not loaded (restart Home Assistant after installing).","error.generic":"Could not load the report: {message}",coverage:"{measured} measured, {estimated} estimated, {excluded} excluded, {missing} missing of {expected} h"},ge={title:"Стоимость электроэнергии",previous:"Назад",next:"Вперёд",now:"Сейчас",refresh:"Обновить",period:"Период",custom:"Свой период",from:"С",to:"По",apply:"Применить",grouping:"Группировка","grouping.auto":"Авто","grouping.hour":"По часам","grouping.day":"По дням","grouping.week":"По неделям","grouping.month":"По месяцам","grouping.hour_too_long":"По часам: до 31 дня","preset.today":"Сегодня","preset.yesterday":"Вчера","preset.this_week":"Эта неделя","preset.last_week":"Прошлая неделя","preset.this_month":"Этот месяц","preset.last_month":"Прошлый месяц","preset.this_quarter":"Этот квартал","preset.this_year":"Этот год","preset.now-7d":"Последние 7 дней","preset.now-30d":"Последние 30 дней","preset.now-12m":"Последние 12 месяцев",device:"Устройство",total:"Итого",kwh:"кВт·ч",cost:"Сумма",avg_price:"Ср. цена",breakdown:"По периодам",breakdown_device:"Показать",all_devices:"Все устройства",data_quality:"Качество данных",loading:"Загрузка…",no_devices:"Не выбраны датчики энергии. Добавьте их в настройках интеграции.",no_plan:"Для этого периода нет тарифного плана: стоимость неизвестна.",unpriced:"{hours} ч до первого тарифного плана не оценены.","status.complete":"Полные данные","status.estimated":"Есть оценочные часы (распределены по пропуску)","status.partial":"Часть часов отсутствует","status.missing":"Нет данных","issue.estimated":"оценка","issue.excluded_negative":"исключено (отрицательное)","issue.excluded_spike":"исключено (выброс)","statistics.no_statistics":"статистики пока нет","statistics.unsupported":"датчик не поддерживается","error.not_loaded":"Energy Cost Stats не настроена или не загружена.","error.invalid_period":"Неверный период.","error.period_too_long":"Период слишком длинный для этой группировки.","error.unknown_entity":"В карточке указан датчик, не выбранный в интеграции.","error.unknown_command":"Интеграция не загружена (перезапустите Home Assistant после установки).","error.generic":"Не удалось загрузить отчёт: {message}",coverage:"{measured} измерено, {estimated} оценено, {excluded} исключено, {missing} нет из {expected} ч"},nt=class{constructor(t){this.locale=t||"en",this.table=this.locale.toLowerCase().startsWith("ru")?ge:pe}t(t,e={}){return this.table[t].replace(/\{(\w+)\}/g,(s,i)=>i in e?String(e[i]):`{${i}}`)}preset(t){return this.t(`preset.${t}`)}grouping(t){return this.t(`grouping.${t}`)}number(t,e){return t==null?"—":new Intl.NumberFormat(this.locale,{minimumFractionDigits:e,maximumFractionDigits:e}).format(Number(t))}money(t,e){if(t==null)return"—";if(e)try{return new Intl.NumberFormat(this.locale,{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(t))}catch{}return this.number(t,2)}avgPrice(t,e){return t===null||e===null||Number(e)===0?"—":this.number(String(Number(t)/Number(e)),2)}date(t,e){return new Intl.DateTimeFormat(this.locale,{...e,timeZone:"UTC"}).format(new Date(`${t}T00:00:00Z`))}periodLabel(t){switch(bt(t)){case"day":return this.date(t.start,{day:"numeric",month:"long",year:"numeric"});case"month":return this.date(t.start,{month:"long",year:"numeric"});case"quarter":return`Q${Math.floor(Number(t.start.slice(5,7))/3)+1} ${t.start.slice(0,4)}`;case"year":return t.start.slice(0,4);case"months":return`${this.date(t.start,{month:"short",year:"numeric"})} – ${this.date(t.end,{month:"short",year:"numeric"})}`;default:{let s=t.start.slice(0,4)===t.end.slice(0,4),i=this.date(t.start,{day:"numeric",month:"short",...s?{}:{year:"numeric"}}),n=this.date(t.end,{day:"numeric",month:"short",year:"numeric"});return`${i} – ${n}`}}}bucketLabel(t,e){let s=t.slice(0,10);switch(e){case"hour":return`${this.date(s,{day:"numeric",month:"short"})} ${t.slice(11,16)}`;case"day":return this.date(s,{weekday:"short",day:"numeric",month:"short"});case"week":return this.date(s,{day:"numeric",month:"short",year:"numeric"});case"month":return this.date(s,{month:"long",year:"numeric"});default:return this.t("total")}}};var me="energy_cost_stats/report";function _e(r){let t={type:me,start:r.period.start,end:rt(r.period,r.timeZone,r.now),grouping:r.grouping};return r.entities&&r.entities.length>0&&(t.entities=r.entities),t}function Zt(r,t){return r.callWS(_e(t))}function Wt(r){if(r&&typeof r=="object"&&"code"in r){let t=r.code;return typeof t=="string"?t:void 0}}function Qt(r){return r&&typeof r=="object"&&"message"in r?String(r.message):String(r)}var A="energy-cost-stats-card",Jt=["auto","hour","day","week","month"],fe=600*1e3,$e="M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",ye="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",ve="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";function At(r){return h`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${r}></path></svg>`}var ot=class extends w{constructor(){super(...arguments);this._groupingChoice="auto";this._loading=!1;this._customOpen=!1;this._customStart="";this._customEnd="";this._breakdownEntity="";this._requestSeq=0;this._lastRequestOpen=!1}static{this.properties={hass:{attribute:!1},_config:{state:!0},_period:{state:!0},_groupingChoice:{state:!0},_report:{state:!0},_error:{state:!0},_loading:{state:!0},_customOpen:{state:!0},_customStart:{state:!0},_customEnd:{state:!0},_breakdownEntity:{state:!0}}}static getStubConfig(){return{type:`custom:${A}`,period:"this_month"}}setConfig(e){if(!e||typeof e!="object")throw new Error("Invalid configuration");if(e.period!==void 0&&!B.includes(e.period))throw new Error(`Unknown period: ${String(e.period)}`);if(e.grouping!==void 0&&!Jt.includes(e.grouping))throw new Error(`Unknown grouping: ${String(e.grouping)}`);if(e.entities!==void 0&&(!Array.isArray(e.entities)||e.entities.some(i=>typeof i!="string")))throw new Error("entities must be a list of entity ids");let s=this._config;this._config=e,this._groupingChoice=e.grouping??"auto",s&&this._period&&(this._period=void 0,this._report=void 0)}getCardSize(){return 3+(this._report?.devices.length??2)}get _strings(){return new nt(this.hass?.locale?.language??this.hass?.language)}get _timeZone(){return this._reportTimeZone??this.hass?.config?.time_zone}_today(){return et(this._timeZone)}get grouping(){let e=this._period;if(!e)return"day";let s=this._groupingChoice;return s!=="auto"&&it(s,e)?s:Yt(e)}connectedCallback(){super.connectedCallback(),this._timer=setInterval(()=>{this._period&&this._lastRequestOpen&&!this._loading&&this._load()},fe)}disconnectedCallback(){super.disconnectedCallback(),this._timer!==void 0&&clearInterval(this._timer),this._timer=void 0}willUpdate(e){this.hass&&this._config&&!this._period&&(this._period=v(this._config.period??"this_month",this._today())),super.willUpdate(e)}updated(e){super.updated(e),!(!this.hass||!this._period)&&(e.has("_period")||e.has("_groupingChoice")||e.has("hass")&&e.get("hass")===void 0)&&this._load()}async _load(){let e=this.hass,s=this._period;if(!e||!s)return;let i=++this._requestSeq,n=this._timeZone;this._loading=!0;try{let o=await Zt(e,{period:s,grouping:this.grouping,entities:this._config?.entities,timeZone:n});if(i!==this._requestSeq)return;this._report=o,this._error=void 0,this._reportTimeZone=o.time_zone,this._lastRequestOpen=rt(s,o.time_zone)!==I(s),o.time_zone!==n&&st(s,et(o.time_zone))&&this._load()}catch(o){if(i!==this._requestSeq)return;let c=Wt(o),d=c?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_command:"error.unknown_command"}[c]:void 0;this._error=d?this._strings.t(d):this._strings.t("error.generic",{message:Qt(o)}),this._report=void 0}finally{i===this._requestSeq&&(this._loading=!1)}}_selectedPreset(){if(!this._period)return"";let e=this._today(),s=this._period;return B.find(i=>{let n=v(i,e);return n.start===s.start&&n.end===s.end})??""}_onPreset(e){let s=e.target.value;if(s==="custom"){this._openCustom();return}B.includes(s)&&(this._customOpen=!1,this._period=v(s,this._today()))}_openCustom(){this._customOpen=!0,this._customStart=this._period?.start??this._today(),this._customEnd=this._period?.end??this._today()}_applyCustom(){let e=this._customStart,s=this._customEnd;!yt(e)||!yt(s)||(this._period=e<=s?{start:e,end:s}:{start:s,end:e},this._customOpen=!1)}_shift(e){this._period&&(this._period=wt(this._period,e))}_now(){this._period&&(this._period=Kt(this._period,this._today()))}_onGrouping(e){this._groupingChoice=e.target.value}render(){if(!this._config||!this.hass||!this._period)return l;let e=this._strings,s=this._config.title??e.t("title");return h`
      <ha-card>
        <div class="header">
          <div class="title">${s}</div>
          ${this._loading?h`<div class="loading" role="status">${e.t("loading")}</div>`:l}
        </div>
        ${this._renderPicker(e)}
        <div class="content">
          ${this._error?h`<div class="error" role="alert">${this._error}</div>`:this._report?this._renderReport(e,this._report):l}
        </div>
      </ha-card>
    `}_renderPicker(e){let s=this._period,i=this._selectedPreset(),n=this._today(),o=st(s,n),c=wt(s,1).start>n;return h`
      <div class="picker">
        <select
          class="preset"
          aria-label=${e.t("period")}
          .value=${X(i)}
          @change=${this._onPreset}
        >
          <option value="" ?hidden=${i!==""} ?selected=${i===""}>
            ${e.t("custom")}
          </option>
          ${B.map(a=>h`<option value=${a} ?selected=${a===i}>${e.preset(a)}</option>`)}
          <option value="custom">${e.t("custom")}…</option>
        </select>
        <div class="nav">
          <button
            class="icon prev"
            title=${e.t("previous")}
            aria-label=${e.t("previous")}
            @click=${()=>this._shift(-1)}
          >
            ${At($e)}
          </button>
          <button class="label" title=${e.t("custom")} @click=${this._openCustom}>
            ${e.periodLabel(s)}
          </button>
          <button
            class="icon next"
            title=${e.t("next")}
            aria-label=${e.t("next")}
            ?disabled=${c}
            @click=${()=>this._shift(1)}
          >
            ${At(ye)}
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
          ${At(ve)}
        </button>
      </div>
      ${this._customOpen?h`<div class="custom">
            <label
              >${e.t("from")}
              <input
                type="date"
                class="custom-start"
                .value=${this._customStart}
                max=${n}
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
    `}_renderReport(e,s){if(s.devices.length===0)return h`<div class="note">${e.t("no_devices")}</div>`;let i=new Map(s.devices.map(c=>[c.entity_id,c])),n=s.totals,o=s.plans.length===0;return h`
      ${o?h`<div class="note warning">${e.t("no_plan")}</div>`:l}
      ${!o&&s.unpriced_hours>0?h`<div class="note warning">
            ${e.t("unpriced",{hours:s.unpriced_hours})}
          </div>`:l}
      <div class="table-wrap">
        <table class="devices">
          ${this._renderHead(e,s,e.t("device"),n)}
          <tbody>
            ${n.rows.map(c=>{let a=c.entity_id?i.get(c.entity_id):void 0,d=a?.name??c.entity_id??"",u=a&&a.statistics!=="ok"?e.t(`statistics.${a.statistics}`):"";return this._renderRow(e,s,c,d,u)})}
          </tbody>
          <tfoot>
            ${this._renderRow(e,s,n.total,e.t("total"),"")}
          </tfoot>
        </table>
      </div>
      ${s.grouping!=="total"?this._renderBreakdown(e,s):l}
      ${s.issues.length>0?this._renderIssues(e,s,i):l}
    `}_renderHead(e,s,i,n){let o=s.currency;return h`
      <thead>
        <tr>
          <th rowspan="2" class="name">${i}</th>
          ${s.zones.map((c,a)=>{let d=n.total.zones[a]?.price??null;return h`<th colspan="2" class="zone">
              ${c.name}${d!==null?h`<span class="price">${e.money(d,o)}</span>`:l}
            </th>`})}
          <th colspan="3" class="zone sum">${e.t("total")}</th>
        </tr>
        <tr>
          ${s.zones.map(()=>h`<th class="num">${e.t("kwh")}</th><th class="num">${e.t("cost")}</th>`)}
          <th class="num">${e.t("kwh")}</th>
          <th class="num">${e.t("cost")}</th>
          <th class="num">${e.t("avg_price")}</th>
        </tr>
      </thead>
    `}_renderRow(e,s,i,n,o){let c=s.currency,a=i.coverage,d=e.t("coverage",{measured:a.measured,estimated:a.estimated,excluded:a.excluded,missing:a.missing,expected:a.expected});return h`
      <tr class="status-${i.status}">
        <th scope="row" class="name">
          <span>${n}</span>
          ${i.status!=="complete"?h`<span
                class="badge ${i.status}"
                title="${e.t(`status.${i.status}`)} · ${d}"
                >${i.status==="estimated"?"≈":"!"}</span
              >`:l}
          ${o?h`<span class="sub">${o}</span>`:l}
        </th>
        ${i.zones.map(u=>h`<td class="num">${e.number(u.kwh,2)}</td>
              <td class="num">${e.money(u.cost,c)}</td>`)}
        <td class="num strong">${e.number(i.kwh,2)}</td>
        <td class="num strong">${e.money(i.cost,c)}</td>
        <td class="num">${e.avgPrice(i.cost,i.kwh)}</td>
      </tr>
    `}_renderBreakdown(e,s){let i=this._breakdownEntity,n=i?s.devices.findIndex(d=>d.entity_id===i):-1,o=d=>(n>=0?d.rows.find(u=>u.entity_id===i):void 0)??d.total,c=this._groupingChoice,a=c==="auto"||it(c,this._period)?c:"auto";return h`
      <details class="breakdown" ?open=${this._config?.show_breakdown??!1}>
        <summary>${e.t("breakdown")}</summary>
        <div class="breakdown-controls">
          <label
            >${e.t("breakdown_device")}
            <select
              class="breakdown-device"
              .value=${X(n>=0?i:"")}
              @change=${d=>{this._breakdownEntity=d.target.value}}
            >
              <option value="">${e.t("all_devices")}</option>
              ${s.devices.map(d=>h`<option value=${d.entity_id} ?selected=${d.entity_id===i}>
                    ${d.name}
                  </option>`)}
            </select>
          </label>
          <label
            >${e.t("grouping")}
            <select class="grouping" .value=${X(a)} @change=${this._onGrouping}>
              ${Jt.map(d=>{let u=d==="auto"||it(d,this._period);return h`<option
                  value=${d}
                  ?disabled=${!u}
                  ?selected=${d===a}
                >
                  ${u?e.grouping(d):e.t("grouping.hour_too_long")}
                </option>`})}
            </select>
          </label>
        </div>
        <div class="table-wrap">
          <table class="buckets">
            ${this._renderHead(e,s,e.t("period"),s.totals)}
            <tbody>
              ${s.buckets.map(d=>this._renderRow(e,s,o(d),this._bucketLabel(e,s,d),""))}
            </tbody>
            <tfoot>
              ${this._renderRow(e,s,o(s.totals),e.t("total"),"")}
            </tfoot>
          </table>
        </div>
      </details>
    `}_bucketLabel(e,s,i){if(s.grouping==="week"){let n=i.start.slice(0,10);return e.periodLabel({start:n,end:g(n,6)})}return e.bucketLabel(i.start,s.grouping)}_renderIssues(e,s,i){return h`
      <details class="issues">
        <summary>${e.t("data_quality")} (${s.issues.length})</summary>
        <ul>
          ${s.issues.map(n=>h`<li>
                <span class="who">${i.get(n.entity_id)?.name??n.entity_id}</span>:
                ${e.t(`issue.${n.kind}`)},
                ${e.bucketLabel(n.start,"hour")} – ${e.bucketLabel(n.end,"hour")}
                (${n.hours} h, ${e.number(n.kwh,3)} ${e.t("kwh")})
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
  `}};var be=3e4;function xt(){let r=window.customElements;r.get(A)||(r.define(A,ot),window.customCards=window.customCards??[],window.customCards.some(t=>t.type===A)||window.customCards.push({type:A,name:"Energy Cost Stats",description:"Electricity cost per device, split by tariff zones",preview:!1}))}function we(){document.querySelector("home-assistant")!==null&&!window.customElements.get("home-assistant")?(window.customElements.whenDefined("home-assistant").then(xt),setTimeout(()=>{window.customElements.get(A)||(console.warn(`${A}: the frontend did not boot in time; defining the card anyway`),xt())},be)):xt()}we();export{be as BOOT_TIMEOUT_MS,xt as defineCard,we as registerCard};
