var j=globalThis,Z=j.ShadowRoot&&(j.ShadyCSS===void 0||j.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,_t=Symbol(),Ht=new WeakMap,N=class{constructor(e,t,r){if(this._$cssResult$=!0,r!==_t)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o,t=this.t;if(Z&&e===void 0){let r=t!==void 0&&t.length===1;r&&(e=Ht.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),r&&Ht.set(t,e))}return e}toString(){return this.cssText}},Ut=n=>new N(typeof n=="string"?n:n+"",void 0,_t),H=(n,...e)=>{let t=n.length===1?n[0]:e.reduce((r,i,s)=>r+(a=>{if(a._$cssResult$===!0)return a.cssText;if(typeof a=="number")return a;throw Error("Value passed to 'css' function must be a 'css' function result: "+a+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+n[s+1],n[0]);return new N(t,n,_t)},zt=(n,e)=>{if(Z)n.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(let t of e){let r=document.createElement("style"),i=j.litNonce;i!==void 0&&r.setAttribute("nonce",i),r.textContent=t.cssText,n.appendChild(r)}},ft=Z?n=>n:n=>n instanceof CSSStyleSheet?(e=>{let t="";for(let r of e.cssRules)t+=r.cssText;return Ut(t)})(n):n;var{is:Se,defineProperty:Ce,getOwnPropertyDescriptor:Ee,getOwnPropertyNames:Ae,getOwnPropertySymbols:Pe,getPrototypeOf:Te}=Object,Y=globalThis,It=Y.trustedTypes,Re=It?It.emptyScript:"",De=Y.reactiveElementPolyfillSupport,U=(n,e)=>n,yt={toAttribute(n,e){switch(e){case Boolean:n=n?Re:null;break;case Object:case Array:n=n==null?n:JSON.stringify(n)}return n},fromAttribute(n,e){let t=n;switch(e){case Boolean:t=n!==null;break;case Number:t=n===null?null:Number(n);break;case Object:case Array:try{t=JSON.parse(n)}catch{t=null}}return t}},qt=(n,e)=>!Se(n,e),Bt={attribute:!0,type:String,converter:yt,reflect:!1,useDefault:!1,hasChanged:qt};Symbol.metadata??=Symbol("metadata"),Y.litPropertyMetadata??=new WeakMap;var w=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=Bt){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){let r=Symbol(),i=this.getPropertyDescriptor(e,r,t);i!==void 0&&Ce(this.prototype,e,i)}}static getPropertyDescriptor(e,t,r){let{get:i,set:s}=Ee(this.prototype,e)??{get(){return this[t]},set(a){this[t]=a}};return{get:i,set(a){let d=i?.call(this);s?.call(this,a),this.requestUpdate(e,d,r)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??Bt}static _$Ei(){if(this.hasOwnProperty(U("elementProperties")))return;let e=Te(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(U("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(U("properties"))){let t=this.properties,r=[...Ae(t),...Pe(t)];for(let i of r)this.createProperty(i,t[i])}let e=this[Symbol.metadata];if(e!==null){let t=litPropertyMetadata.get(e);if(t!==void 0)for(let[r,i]of t)this.elementProperties.set(r,i)}this._$Eh=new Map;for(let[t,r]of this.elementProperties){let i=this._$Eu(t,r);i!==void 0&&this._$Eh.set(i,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){let t=[];if(Array.isArray(e)){let r=new Set(e.flat(1/0).reverse());for(let i of r)t.unshift(ft(i))}else e!==void 0&&t.push(ft(e));return t}static _$Eu(e,t){let r=t.attribute;return r===!1?void 0:typeof r=="string"?r:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),this.renderRoot!==void 0&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){let e=new Map,t=this.constructor.elementProperties;for(let r of t.keys())this.hasOwnProperty(r)&&(e.set(r,this[r]),delete this[r]);e.size>0&&(this._$Ep=e)}createRenderRoot(){let e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return zt(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,r){this._$AK(e,r)}_$ET(e,t){let r=this.constructor.elementProperties.get(e),i=this.constructor._$Eu(e,r);if(i!==void 0&&r.reflect===!0){let s=(r.converter?.toAttribute!==void 0?r.converter:yt).toAttribute(t,r.type);this._$Em=e,s==null?this.removeAttribute(i):this.setAttribute(i,s),this._$Em=null}}_$AK(e,t){let r=this.constructor,i=r._$Eh.get(e);if(i!==void 0&&this._$Em!==i){let s=r.getPropertyOptions(i),a=typeof s.converter=="function"?{fromAttribute:s.converter}:s.converter?.fromAttribute!==void 0?s.converter:yt;this._$Em=i;let d=a.fromAttribute(t,s.type);this[i]=d??this._$Ej?.get(i)??d,this._$Em=null}}requestUpdate(e,t,r,i=!1,s){if(e!==void 0){let a=this.constructor;if(i===!1&&(s=this[e]),r??=a.getPropertyOptions(e),!((r.hasChanged??qt)(s,t)||r.useDefault&&r.reflect&&s===this._$Ej?.get(e)&&!this.hasAttribute(a._$Eu(e,r))))return;this.C(e,t,r)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:r,reflect:i,wrapped:s},a){r&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,a??t??this[e]),s!==!0||a!==void 0)||(this._$AL.has(e)||(this.hasUpdated||r||(t=void 0),this._$AL.set(e,t)),i===!0&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}let e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[i,s]of this._$Ep)this[i]=s;this._$Ep=void 0}let r=this.constructor.elementProperties;if(r.size>0)for(let[i,s]of r){let{wrapped:a}=s,d=this[i];a!==!0||this._$AL.has(i)||d===void 0||this.C(i,void 0,s,d)}}let e=!1,t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(r=>r.hostUpdate?.()),this.update(t)):this._$EM()}catch(r){throw e=!1,this._$EM(),r}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(e){}firstUpdated(e){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[U("elementProperties")]=new Map,w[U("finalized")]=new Map,De?.({ReactiveElement:w}),(Y.reactiveElementVersions??=[]).push("2.1.2");var $t=globalThis,Ft=n=>n,W=$t.trustedTypes,Kt=W?W.createPolicy("lit-html",{createHTML:n=>n}):void 0,bt="$lit$",k=`lit$${Math.random().toFixed(9).slice(2)}$`,wt="?"+k,Me=`<${wt}>`,A=document,I=()=>A.createComment(""),B=n=>n===null||typeof n!="object"&&typeof n!="function",kt=Array.isArray,Wt=n=>kt(n)||typeof n?.[Symbol.iterator]=="function",vt=`[ 	
\f\r]`,z=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Vt=/-->/g,Gt=/>/g,C=RegExp(`>|${vt}(?:([^\\s"'>=/]+)(${vt}*=${vt}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),jt=/'/g,Zt=/"/g,Qt=/^(?:script|style|textarea|title)$/i,xt=n=>(e,...t)=>({_$litType$:n,strings:e,values:t}),h=xt(1),or=xt(2),ar=xt(3),f=Symbol.for("lit-noChange"),p=Symbol.for("lit-nothing"),Yt=new WeakMap,E=A.createTreeWalker(A,129);function Jt(n,e){if(!kt(n)||!n.hasOwnProperty("raw"))throw Error("invalid template strings array");return Kt!==void 0?Kt.createHTML(e):e}var Xt=(n,e)=>{let t=n.length-1,r=[],i,s=e===2?"<svg>":e===3?"<math>":"",a=z;for(let d=0;d<t;d++){let c=n[d],o,l,u=-1,g=0;for(;g<c.length&&(a.lastIndex=g,l=a.exec(c),l!==null);)g=a.lastIndex,a===z?l[1]==="!--"?a=Vt:l[1]!==void 0?a=Gt:l[2]!==void 0?(Qt.test(l[2])&&(i=RegExp("</"+l[2],"g")),a=C):l[3]!==void 0&&(a=C):a===C?l[0]===">"?(a=i??z,u=-1):l[1]===void 0?u=-2:(u=a.lastIndex-l[2].length,o=l[1],a=l[3]===void 0?C:l[3]==='"'?Zt:jt):a===Zt||a===jt?a=C:a===Vt||a===Gt?a=z:(a=C,i=void 0);let m=a===C&&n[d+1].startsWith("/>")?" ":"";s+=a===z?c+Me:u>=0?(r.push(o),c.slice(0,u)+bt+c.slice(u)+k+m):c+k+(u===-2?d:m)}return[Jt(n,s+(n[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),r]},q=class n{constructor({strings:e,_$litType$:t},r){let i;this.parts=[];let s=0,a=0,d=e.length-1,c=this.parts,[o,l]=Xt(e,t);if(this.el=n.createElement(o,r),E.currentNode=this.el.content,t===2||t===3){let u=this.el.content.firstChild;u.replaceWith(...u.childNodes)}for(;(i=E.nextNode())!==null&&c.length<d;){if(i.nodeType===1){if(i.hasAttributes())for(let u of i.getAttributeNames())if(u.endsWith(bt)){let g=l[a++],m=i.getAttribute(u).split(k),b=/([.?@])?(.*)/.exec(g);c.push({type:1,index:s,name:b[2],strings:m,ctor:b[1]==="."?J:b[1]==="?"?X:b[1]==="@"?tt:T}),i.removeAttribute(u)}else u.startsWith(k)&&(c.push({type:6,index:s}),i.removeAttribute(u));if(Qt.test(i.tagName)){let u=i.textContent.split(k),g=u.length-1;if(g>0){i.textContent=W?W.emptyScript:"";for(let m=0;m<g;m++)i.append(u[m],I()),E.nextNode(),c.push({type:2,index:++s});i.append(u[g],I())}}}else if(i.nodeType===8)if(i.data===wt)c.push({type:2,index:s});else{let u=-1;for(;(u=i.data.indexOf(k,u+1))!==-1;)c.push({type:7,index:s}),u+=k.length-1}s++}}static createElement(e,t){let r=A.createElement("template");return r.innerHTML=e,r}};function P(n,e,t=n,r){if(e===f)return e;let i=r!==void 0?t._$Co?.[r]:t._$Cl,s=B(e)?void 0:e._$litDirective$;return i?.constructor!==s&&(i?._$AO?.(!1),s===void 0?i=void 0:(i=new s(n),i._$AT(n,t,r)),r!==void 0?(t._$Co??=[])[r]=i:t._$Cl=i),i!==void 0&&(e=P(n,i._$AS(n,e.values),i,r)),e}var Q=class{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){let{el:{content:t},parts:r}=this._$AD,i=(e?.creationScope??A).importNode(t,!0);E.currentNode=i;let s=E.nextNode(),a=0,d=0,c=r[0];for(;c!==void 0;){if(a===c.index){let o;c.type===2?o=new M(s,s.nextSibling,this,e):c.type===1?o=new c.ctor(s,c.name,c.strings,this,e):c.type===6&&(o=new et(s,this,e)),this._$AV.push(o),c=r[++d]}a!==c?.index&&(s=E.nextNode(),a++)}return E.currentNode=A,i}p(e){let t=0;for(let r of this._$AV)r!==void 0&&(r.strings!==void 0?(r._$AI(e,r,t),t+=r.strings.length-2):r._$AI(e[t])),t++}},M=class n{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,r,i){this.type=2,this._$AH=p,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=r,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode,t=this._$AM;return t!==void 0&&e?.nodeType===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=P(this,e,t),B(e)?e===p||e==null||e===""?(this._$AH!==p&&this._$AR(),this._$AH=p):e!==this._$AH&&e!==f&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Wt(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==p&&B(this._$AH)?this._$AA.nextSibling.data=e:this.T(A.createTextNode(e)),this._$AH=e}$(e){let{values:t,_$litType$:r}=e,i=typeof r=="number"?this._$AC(e):(r.el===void 0&&(r.el=q.createElement(Jt(r.h,r.h[0]),this.options)),r);if(this._$AH?._$AD===i)this._$AH.p(t);else{let s=new Q(i,this),a=s.u(this.options);s.p(t),this.T(a),this._$AH=s}}_$AC(e){let t=Yt.get(e.strings);return t===void 0&&Yt.set(e.strings,t=new q(e)),t}k(e){kt(this._$AH)||(this._$AH=[],this._$AR());let t=this._$AH,r,i=0;for(let s of e)i===t.length?t.push(r=new n(this.O(I()),this.O(I()),this,this.options)):r=t[i],r._$AI(s),i++;i<t.length&&(this._$AR(r&&r._$AB.nextSibling,i),t.length=i)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){let r=Ft(e).nextSibling;Ft(e).remove(),e=r}}setConnected(e){this._$AM===void 0&&(this._$Cv=e,this._$AP?.(e))}},T=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,r,i,s){this.type=1,this._$AH=p,this._$AN=void 0,this.element=e,this.name=t,this._$AM=i,this.options=s,r.length>2||r[0]!==""||r[1]!==""?(this._$AH=Array(r.length-1).fill(new String),this.strings=r):this._$AH=p}_$AI(e,t=this,r,i){let s=this.strings,a=!1;if(s===void 0)e=P(this,e,t,0),a=!B(e)||e!==this._$AH&&e!==f,a&&(this._$AH=e);else{let d=e,c,o;for(e=s[0],c=0;c<s.length-1;c++)o=P(this,d[r+c],t,c),o===f&&(o=this._$AH[c]),a||=!B(o)||o!==this._$AH[c],o===p?e=p:e!==p&&(e+=(o??"")+s[c+1]),this._$AH[c]=o}a&&!i&&this.j(e)}j(e){e===p?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}},J=class extends T{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===p?void 0:e}},X=class extends T{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==p)}},tt=class extends T{constructor(e,t,r,i,s){super(e,t,r,i,s),this.type=5}_$AI(e,t=this){if((e=P(this,e,t,0)??p)===f)return;let r=this._$AH,i=e===p&&r!==p||e.capture!==r.capture||e.once!==r.once||e.passive!==r.passive,s=e!==p&&(r===p||i);i&&this.element.removeEventListener(this.name,this,r),s&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}},et=class{constructor(e,t,r){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=r}get _$AU(){return this._$AM._$AU}_$AI(e){P(this,e)}},te={M:bt,P:k,A:wt,C:1,L:Xt,R:Q,D:Wt,V:P,I:M,H:T,N:X,U:tt,B:J,F:et},Le=$t.litHtmlPolyfillSupport;Le?.(q,M),($t.litHtmlVersions??=[]).push("3.3.3");var ee=(n,e,t)=>{let r=t?.renderBefore??e,i=r._$litPart$;if(i===void 0){let s=t?.renderBefore??null;r._$litPart$=i=new M(e.insertBefore(I(),s),s,void 0,t??{})}return i._$AI(n),i};var St=globalThis,$=class extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){let t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=ee(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return f}};$._$litElement$=!0,$.finalized=!0,St.litElementHydrateSupport?.({LitElement:$});var Oe=St.litElementPolyfillSupport;Oe?.({LitElement:$});(St.litElementVersions??=[]).push("4.2.2");var R={ATTRIBUTE:1,CHILD:2,PROPERTY:3,BOOLEAN_ATTRIBUTE:4,EVENT:5,ELEMENT:6},re=n=>(...e)=>({_$litDirective$:n,values:e}),rt=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,r){this._$Ct=e,this._$AM=t,this._$Ci=r}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}};var{I:wr}=te;var ne=n=>n.strings===void 0;var Ne={},ie=(n,e=Ne)=>n._$AH=e;var nt=re(class extends rt{constructor(n){if(super(n),n.type!==R.PROPERTY&&n.type!==R.ATTRIBUTE&&n.type!==R.BOOLEAN_ATTRIBUTE)throw Error("The `live` directive is not allowed on child or event bindings");if(!ne(n))throw Error("`live` bindings can only contain a single expression")}render(n){return n}update(n,[e]){if(e===f||e===p)return e;let t=n.element,r=n.name;if(n.type===R.PROPERTY){if(e===t[r])return f}else if(n.type===R.BOOLEAN_ATTRIBUTE){if(!!e===t.hasAttribute(r))return f}else if(n.type===R.ATTRIBUTE&&t.getAttribute(r)===e+"")return f;return ie(n),e}});var K=["today","yesterday","this_week","last_week","this_month","last_month","this_quarter","this_year","now-7d","now-30d","now-12m"];function y(n){let e=/^(\d{4})-(\d{2})-(\d{2})$/.exec(n);if(!e)throw new Error(`invalid date: ${n}`);let[,t,r,i]=e;return new Date(Date.UTC(Number(t),Number(r)-1,Number(i)))}function it(n){return n.toISOString().slice(0,10)}function Et(n){try{return it(y(n))===n}catch{return!1}}function _(n,e){return it(new Date(y(n).getTime()+e*864e5))}function L(n,e=0){let t=y(n);return it(new Date(Date.UTC(t.getUTCFullYear(),t.getUTCMonth()+e,1)))}function D(n,e=0){let t=y(n);return it(new Date(Date.UTC(t.getUTCFullYear(),t.getUTCMonth()+e+1,0)))}function Ct(n){let e=(y(n).getUTCDay()+6)%7;return _(n,-e)}function V(n){return Math.round((y(n.end).getTime()-y(n.start).getTime())/864e5)+1}function At(n){let e=y(n.start);if(e.getUTCDate()!==1||D(n.end)!==n.end)return null;let t=y(n.end);return(t.getUTCFullYear()-e.getUTCFullYear())*12+(t.getUTCMonth()-e.getUTCMonth())+1}function S(n,e=new Date){let t={year:"numeric",month:"2-digit",day:"2-digit"},r;try{r=new Intl.DateTimeFormat("en-CA",{...t,timeZone:n}).formatToParts(e)}catch{r=new Intl.DateTimeFormat("en-CA",t).formatToParts(e)}let i=s=>r.find(a=>a.type===s)?.value??"";return`${i("year")}-${i("month")}-${i("day")}`}function x(n,e){switch(n){case"today":return{start:e,end:e};case"yesterday":{let t=_(e,-1);return{start:t,end:t}}case"this_week":{let t=Ct(e);return{start:t,end:_(t,6)}}case"last_week":{let t=_(Ct(e),-7);return{start:t,end:_(t,6)}}case"this_month":return{start:L(e),end:D(e)};case"last_month":return{start:L(e,-1),end:D(e,-1)};case"this_quarter":{let t=y(e).getUTCMonth(),r=L(e,-(t%3));return{start:r,end:D(r,2)}}case"this_year":{let t=e.slice(0,4);return{start:`${t}-01-01`,end:`${t}-12-31`}}case"now-7d":return{start:_(e,-6),end:e};case"now-30d":return{start:_(e,-29),end:e};case"now-12m":return{start:L(e,-11),end:D(e)}}}function Pt(n){let e=At(n);if(e!==null){let r=y(n.start).getUTCMonth();return e===1?"month":e===3&&r%3===0?"quarter":e===12&&r===0?"year":"months"}let t=V(n);return t===1?"day":t===7&&Ct(n.start)===n.start?"week":"days"}function Tt(n,e){let t=At(n);if(t!==null){let i=t*e;return{start:L(n.start,i),end:D(n.end,i)}}let r=V(n)*e;return{start:_(n.start,r),end:_(n.end,r)}}function se(n,e){switch(Pt(n)){case"day":return x("today",e);case"week":return x("this_week",e);case"month":return x("this_month",e);case"quarter":return x("this_quarter",e);case"year":return x("this_year",e);case"months":{let r=At(n)??1;return{start:L(e,-(r-1)),end:D(e)}}case"days":return{start:_(e,-(V(n)-1)),end:e}}}function st(n,e){return n.start<=e&&e<=n.end}function F(n){return _(n.end,1)}function ot(n,e,t=new Date){let r=S(e,t);if(!st(n,r))return F(n);let i;try{i=new Intl.DateTimeFormat("en-GB",{timeZone:e,hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(t)}catch{return F(n)}let s=Number(i.find(o=>o.type==="hour")?.value),a=Number(i.find(o=>o.type==="minute")?.value);if(!Number.isFinite(s)||a!==t.getUTCMinutes())return F(n);let d=n.start===r?Math.max(s,1):s,c=He(e,t,d-s);return`${r}T${String(d).padStart(2,"0")}:00:00${c}`}function He(n,e,t){let r=new Date(e.getTime()+t*36e5),i=new Intl.DateTimeFormat("en-US",{timeZone:n,timeZoneName:"longOffset"}).formatToParts(r).find(a=>a.type==="timeZoneName")?.value??"GMT",s=/^GMT([+-]\d{2}):?(\d{2})?$/.exec(i);return s?`${s[1]}:${s[2]??"00"}`:"+00:00"}var Ue=31;function oe(n){let e=V(n);return e<=2?"hour":e<=45?"day":e<=120?"week":"month"}function at(n,e){return n!=="hour"||V(e)<=Ue}var ae="energy_";function ze(n,e){return n?[`_${n}`]:e?[`_${ae}${e}`]:[]}function ce(n){return n.startsWith(ae)}function Rt(n,e){return n||e.split("/").filter(Boolean)[0]}function Ie(n){if(!n||typeof n!="object")return!1;let e=n;return e.start instanceof Date&&typeof e.subscribe=="function"}function Dt(n,e,t){if(!(!n||typeof n!="object"))for(let r of ze(e,t)){let i=n[r];if(Ie(i))return i}}function de(n,e){return n?.time_zone==="server"?e:void 0}function le(n,e){if(!(n.start instanceof Date)||Number.isNaN(n.start.getTime()))return;let t=S(e,n.start),r=n.end instanceof Date&&!Number.isNaN(n.end.getTime())?S(e,n.end):S(e);return r<t?void 0:{start:t,end:r}}var Be={title:"Energy cost",previous:"Previous",next:"Next",now:"Now",refresh:"Refresh",menu:"Menu",period:"Period",custom:"Custom period",from:"From",to:"To",apply:"Apply",grouping:"Grouping","grouping.auto":"Auto","grouping.hour":"Hours","grouping.day":"Days","grouping.week":"Weeks","grouping.month":"Months","grouping.hour_too_long":"Hours: up to 31 days","preset.today":"Today","preset.yesterday":"Yesterday","preset.this_week":"This week","preset.last_week":"Last week","preset.this_month":"This month","preset.last_month":"Last month","preset.this_quarter":"This quarter","preset.this_year":"This year","preset.now-7d":"Last 7 days","preset.now-30d":"Last 30 days","preset.now-12m":"Last 12 months",device:"Device",total:"Total",kwh:"kWh",cost:"Cost",avg_price:"Avg. price","sort.by":"Sort by {column}, {direction}","sort.ascending":"ascending","sort.descending":"descending","sort.cost_of":"{zone} cost","sort.total_cost":"total cost",breakdown:"By period",breakdown_device:"Show",all_devices:"All devices",data_quality:"Data quality",loading:"Loading…",no_devices:"No energy sensors selected. Add them in the integration options.",no_plan:"No tariff plan covers this period: costs are unknown.",unpriced:"{hours} h before the first tariff plan are not priced.","status.complete":"Complete","status.estimated":"Contains estimated hours (spread over a data gap)","status.partial":"Some hours are missing","status.missing":"No data","issue.estimated":"estimated","issue.excluded_negative":"excluded (negative)","issue.excluded_spike":"excluded (spike)","statistics.no_statistics":"no statistics yet","statistics.unsupported":"unsupported sensor","error.not_loaded":"Energy Cost Stats is not set up or not loaded.","error.invalid_period":"Invalid period.","error.period_too_long":"The period is too long for this grouping.","error.unknown_entity":"The card lists a sensor that is not selected in the integration.","error.unknown_command":"The integration is not loaded (restart Home Assistant after installing).","error.generic":"Could not load the report: {message}","compare.title":"Tariff comparison","compare.tariff":"Tariff","compare.actual":"Actual","compare.difference":"Difference","compare.empty":"No tariffs to compare. Choose them in the integration options (Configure → Compare).","compare.unpriced":"{hours} h not priced by this tariff — the difference covers only the priced hours","compare.unpriced_actual":"{hours} h not priced by the actual schedule — the difference covers only the priced hours","compare.error":"Could not load the comparison: {message}","error.unknown_tariff":"A tariff in the comparison list is not defined in the integration.","nested.title":"Measured inside {name}; not counted again in the total","nested.note":"Indented rows are measured inside the device above them. The total counts their energy only for hours where the device above has no data.",coverage:"{measured} measured, {estimated} estimated, {excluded} excluded, {missing} missing of {expected} h",energy_picker_followed:"Period from the Energy date picker on this dashboard",energy_picker_missing:'No Energy date picker on this dashboard: add the "Energy date selection" card or set period_source: card.'},qe={title:"Стоимость электроэнергии",previous:"Назад",next:"Вперёд",now:"Сейчас",refresh:"Обновить",menu:"Меню",period:"Период",custom:"Свой период",from:"С",to:"По",apply:"Применить",grouping:"Группировка","grouping.auto":"Авто","grouping.hour":"По часам","grouping.day":"По дням","grouping.week":"По неделям","grouping.month":"По месяцам","grouping.hour_too_long":"По часам: до 31 дня","preset.today":"Сегодня","preset.yesterday":"Вчера","preset.this_week":"Эта неделя","preset.last_week":"Прошлая неделя","preset.this_month":"Этот месяц","preset.last_month":"Прошлый месяц","preset.this_quarter":"Этот квартал","preset.this_year":"Этот год","preset.now-7d":"Последние 7 дней","preset.now-30d":"Последние 30 дней","preset.now-12m":"Последние 12 месяцев",device:"Устройство",total:"Итого",kwh:"кВт·ч",cost:"Сумма",avg_price:"Ср. цена","sort.by":"Сортировать по: {column}, {direction}","sort.ascending":"по возрастанию","sort.descending":"по убыванию","sort.cost_of":"стоимость {zone}","sort.total_cost":"общая стоимость",breakdown:"По периодам",breakdown_device:"Показать",all_devices:"Все устройства",data_quality:"Качество данных",loading:"Загрузка…",no_devices:"Не выбраны датчики энергии. Добавьте их в настройках интеграции.",no_plan:"Для этого периода нет тарифного плана: стоимость неизвестна.",unpriced:"{hours} ч до первого тарифного плана не оценены.","status.complete":"Полные данные","status.estimated":"Есть оценочные часы (распределены по пропуску)","status.partial":"Часть часов отсутствует","status.missing":"Нет данных","issue.estimated":"оценка","issue.excluded_negative":"исключено (отрицательное)","issue.excluded_spike":"исключено (выброс)","statistics.no_statistics":"статистики пока нет","statistics.unsupported":"датчик не поддерживается","error.not_loaded":"Energy Cost Stats не настроена или не загружена.","error.invalid_period":"Неверный период.","error.period_too_long":"Период слишком длинный для этой группировки.","error.unknown_entity":"В карточке указан датчик, не выбранный в интеграции.","error.unknown_command":"Интеграция не загружена (перезапустите Home Assistant после установки).","error.generic":"Не удалось загрузить отчёт: {message}","compare.title":"Сравнение тарифов","compare.tariff":"Тариф","compare.actual":"Фактически","compare.difference":"Разница","compare.empty":"Нет тарифов для сравнения. Выберите их в настройках интеграции (Настроить → Сравнение тарифов).","compare.unpriced":"{hours} ч не оценены этим тарифом — разница учитывает только оценённые часы","compare.unpriced_actual":"{hours} ч не оценены фактическим расписанием — разница учитывает только оценённые часы","compare.error":"Не удалось загрузить сравнение: {message}","error.unknown_tariff":"Тариф из списка сравнения не определён в интеграции.","nested.title":"Измеряется внутри «{name}»; в итоге повторно не учитывается","nested.note":"Строки со сдвигом измеряются внутри устройства выше. Итог учитывает их энергию только за часы, когда у устройства выше нет данных.",coverage:"{measured} измерено, {estimated} оценено, {excluded} исключено, {missing} нет из {expected} ч",energy_picker_followed:"Период из выбора периода «Энергия» на этом дашборде",energy_picker_missing:"На дашборде нет выбора периода «Энергия»: добавьте карточку «Выбор даты энергии» или укажите period_source: card."},O=class{constructor(e){this.locale=e||"en",this.table=this.locale.toLowerCase().startsWith("ru")?qe:Be}t(e,t={}){return this.table[e].replace(/\{(\w+)\}/g,(r,i)=>i in t?String(t[i]):`{${i}}`)}preset(e){return this.t(`preset.${e}`)}grouping(e){return this.t(`grouping.${e}`)}number(e,t){return e==null?"—":new Intl.NumberFormat(this.locale,{minimumFractionDigits:t,maximumFractionDigits:t}).format(Number(e))}money(e,t,r=!1){if(e==null)return"—";if(t)try{return new Intl.NumberFormat(this.locale,{style:"currency",currency:t,minimumFractionDigits:2,maximumFractionDigits:2,...r?{signDisplay:"exceptZero"}:{}}).format(Number(e))}catch{}return r?new Intl.NumberFormat(this.locale,{minimumFractionDigits:2,maximumFractionDigits:2,signDisplay:"exceptZero"}).format(Number(e)):this.number(e,2)}signedMoney(e,t){return e===null?"—":this.money(String(e),t,!0)}signedPercent(e){return e===null?"—":`${new Intl.NumberFormat(this.locale,{minimumFractionDigits:1,maximumFractionDigits:1,signDisplay:"exceptZero"}).format(e)} %`}avgPrice(e,t){return e===null||t===null||Number(t)===0?"—":this.number(String(Number(e)/Number(t)),2)}date(e,t){return new Intl.DateTimeFormat(this.locale,{...t,timeZone:"UTC"}).format(new Date(`${e}T00:00:00Z`))}periodLabel(e){switch(Pt(e)){case"day":return this.date(e.start,{day:"numeric",month:"long",year:"numeric"});case"month":return this.date(e.start,{month:"long",year:"numeric"});case"quarter":return`Q${Math.floor(Number(e.start.slice(5,7))/3)+1} ${e.start.slice(0,4)}`;case"year":return e.start.slice(0,4);case"months":return`${this.date(e.start,{month:"short",year:"numeric"})} – ${this.date(e.end,{month:"short",year:"numeric"})}`;default:{let r=e.start.slice(0,4)===e.end.slice(0,4),i=this.date(e.start,{day:"numeric",month:"short",...r?{}:{year:"numeric"}}),s=this.date(e.end,{day:"numeric",month:"short",year:"numeric"});return`${i} – ${s}`}}}bucketLabel(e,t){let r=e.slice(0,10);switch(t){case"hour":return`${this.date(r,{day:"numeric",month:"short"})} ${e.slice(11,16)}`;case"day":return this.date(r,{weekday:"short",day:"numeric",month:"short"});case"week":return this.date(r,{day:"numeric",month:"short",year:"numeric"});case"month":return this.date(r,{month:"long",year:"numeric"});default:return this.t("total")}}};function ue(n,e){if(n===null||e===null)return{amount:null,percent:null};let t=Number(n),r=Number(e);if(!Number.isFinite(t)||!Number.isFinite(r))return{amount:null,percent:null};let i=r-t;return{amount:i,percent:t===0?null:i/t*100}}function pe(n,e){let t=new Set(n.map(c=>c.entity_id)),r=new Map,i=[];for(let c of n){let o=c.upstream;if(o&&o!==c.entity_id&&t.has(o)){let l=r.get(o)??[];l.push(c.entity_id),r.set(o,l)}else i.push(c.entity_id)}if(e){i.sort(e);for(let c of r.values())c.sort(e)}let s=[],a=new Set,d=(c,o)=>{if(!a.has(c)){a.add(c),s.push({entity_id:c,depth:o});for(let l of r.get(c)??[])d(l,o+1)}};for(let c of i)d(c,0);for(let c of n)d(c.entity_id,0);return s}function ct(n,e){return e===void 0||n===void 0?n!==e:n.language!==e.language||n.locale?.language!==e.locale?.language||n.config?.time_zone!==e.config?.time_zone}var Fe=["name","total","avg_price"],lt={sort:"total",direction:"desc"};function ut(n){return n==="name"?"asc":"desc"}function he(n,e){if(n!==void 0&&(typeof n!="string"||n===""))throw new Error("sort must be name, total, avg_price or a zone key");if(e!==void 0&&e!=="asc"&&e!=="desc")throw new Error(`sort_direction must be asc or desc, not ${String(e)}`)}function ge(n,e){return Fe.includes(n.sort)||e.includes(n.sort)?n:lt}function dt(n){if(n==null)return null;let e=Number(n);return Number.isFinite(e)?e:null}function Ke(n,e){if(e==="total")return dt(n.cost);if(e==="avg_price"){let r=dt(n.cost),i=dt(n.kwh);if(r===null||i===null||i<=0)return null;let s=r/i;return Number.isFinite(s)?s:null}let t=n.zones.find(r=>r.key===e);return t?dt(t.cost):null}function me(n,e,t,r){let i=new Intl.Collator(r,{sensitivity:"base",numeric:!0}),s=n.direction==="asc"?1:-1,a=o=>t.get(o)??o,d=(o,l)=>i.compare(a(o),a(l))||(o<l?-1:o>l?1:0);if(n.sort==="name")return(o,l)=>{let u=i.compare(a(o),a(l));return u!==0?s*u:o<l?-1:o>l?1:0};let c=o=>{let l=e.get(o);return l?Ke(l,n.sort):null};return(o,l)=>{let u=c(o),g=c(l);return u!==null&&g!==null&&u!==g?s*(u<g?-1:1):u===null&&g!==null?1:u!==null&&g===null?-1:d(o,l)}}function _e(n,e){let t=JSON.stringify([e.title??null,e.entities??null,e.sort??null,e.sort_direction??null]);return`energy-cost-stats-card.sort.v1|${n}|${t}`}function fe(n){try{let e=localStorage.getItem(n);if(!e)return;let t=JSON.parse(e);if(t&&typeof t.sort=="string"&&t.sort!==""&&(t.direction==="asc"||t.direction==="desc"))return{sort:t.sort,direction:t.direction}}catch{}}function ye(n,e){try{localStorage.setItem(n,JSON.stringify(e))}catch{}}var Ve="energy_cost_stats/report",Ge="energy_cost_stats/compare";function ve(n,e){let t={type:n,start:e.period.start,end:ot(e.period,e.timeZone,e.now)};return e.entities&&e.entities.length>0&&(t.entities=e.entities),t}function je(n){let{type:e,start:t,end:r,entities:i}=ve(Ve,n),s={type:e,start:t,end:r,grouping:n.grouping};return i!==void 0&&(s.entities=i),s}function Ze(n){return ve(Ge,n)}function $e(n,e){return n.callWS(Ze(e))}function be(n,e){return n.callWS(je(e))}function pt(n){if(n&&typeof n=="object"&&"code"in n){let e=n.code;return typeof e=="string"?e:void 0}}function Mt(n){return n&&typeof n=="object"&&"message"in n?String(n.message):String(n)}var v="energy-cost-stats-card",we=["auto","hour","day","week","month"],Ye=["card","energy"],We=600*1e3,Qe="M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",Je="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",ke="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";function ht(n){return h`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${n}></path></svg>`}var gt=class extends ${constructor(){super(...arguments);this._groupingChoice="auto";this._compareLoading=!1;this._compareHidden=!1;this._loading=!1;this._customOpen=!1;this._customStart="";this._customEnd="";this._breakdownEntity="";this._storageKey="";this._requestSeq=0;this._compareSeq=0;this._lastRequestOpen=!1}static{this.properties={hass:{attribute:!1,noAccessor:!0},_config:{state:!0},_period:{state:!0},_groupingChoice:{state:!0},_report:{state:!0},_compare:{state:!0},_compareError:{state:!0},_compareLoading:{state:!0},_compareHidden:{state:!0},_error:{state:!0},_loading:{state:!0},_customOpen:{state:!0},_customStart:{state:!0},_customEnd:{state:!0},_breakdownEntity:{state:!0},_sortChoice:{state:!0}}}static getStubConfig(){return{type:`custom:${v}`,period:"this_month"}}setConfig(t){if(!t||typeof t!="object")throw new Error("Invalid configuration");if(t.period!==void 0&&!K.includes(t.period))throw new Error(`Unknown period: ${String(t.period)}`);if(t.grouping!==void 0&&!we.includes(t.grouping))throw new Error(`Unknown grouping: ${String(t.grouping)}`);if(t.entities!==void 0&&(!Array.isArray(t.entities)||t.entities.some(i=>typeof i!="string")))throw new Error("entities must be a list of entity ids");if(he(t.sort,t.sort_direction),t.period_source!==void 0&&!Ye.includes(t.period_source))throw new Error(`Unknown period_source: ${String(t.period_source)}`);if(t.collection_key!==void 0&&(typeof t.collection_key!="string"||!ce(t.collection_key)))throw new Error('collection_key must start with "energy_" (as in the energy date picker)');let r=this._config;r&&(this._detachEnergy(),this._energyBroken=void 0),this._config=t,this._storageKey=_e(globalThis.location?.pathname??"",t),this._sortChoice=fe(this._storageKey),this._groupingChoice=t.grouping??"auto",r&&this._period&&(this._period=void 0,this._report=void 0,this._compare=void 0)}getCardSize(){let t=this._compare&&!this._compareHidden?this._compare.tariffs.length+3:0;return 3+(this._report?.devices.length??2)+t}getGridOptions(){return{columns:"full",min_columns:6}}get _strings(){return new O(this.hass?.locale?.language??this.hass?.language)}get _timeZone(){return this._reportTimeZone??this.hass?.config?.time_zone}_today(){return S(this._timeZone)}get grouping(){let t=this._period;if(!t)return"day";let r=this._groupingChoice;return r!=="auto"&&at(r,t)?r:oe(t)}get hass(){return this._hass}set hass(t){let r=this._hass;this._hass=t;let i=!1;if(this._config?.period_source==="energy"&&!this._energy){let s=Dt(t?.connection,this._config.collection_key,Rt(t?.panelUrl,window.location.pathname));i=s!==void 0&&s!==this._energyBroken}(i||ct(t,r))&&this.requestUpdate("hass",r)}connectedCallback(){super.connectedCallback(),typeof ResizeObserver<"u"&&(this._controlsObserver=new ResizeObserver(t=>{let r=t[t.length-1];if(!r)return;let i=r.target.getBoundingClientRect().height;this.style.setProperty("--energy-cost-stats-controls-height",`${Math.ceil(i)}px`)})),this._observeControls(),this._timer=setInterval(()=>{this._period&&this._lastRequestOpen&&!this._loading&&this._load()},We)}disconnectedCallback(){super.disconnectedCallback(),this._timer!==void 0&&clearInterval(this._timer),this._timer=void 0,this._detachEnergy(),this._controlsObserver?.disconnect(),this._controlsObserver=void 0,this._observedControls=void 0}_observeControls(){let t=this._controlsObserver;if(!t)return;let r=this.shadowRoot?.querySelector(".controls")??void 0;r!==this._observedControls&&(this._observedControls&&t.unobserve(this._observedControls),this._observedControls=r,r&&t.observe(r))}willUpdate(t){this.hass&&this._config&&this.isConnected&&!this._energy&&this._attachEnergy(),this.hass&&this._config&&!this._period&&(this._period=x(this._config.period??"this_month",this._today())),super.willUpdate(t)}get followsEnergyPicker(){return this._energy!==void 0}_attachEnergy(){if(this._config?.period_source!=="energy")return;let t=Dt(this.hass?.connection,this._config.collection_key,Rt(this.hass?.panelUrl,window.location.pathname));if(!t||t===this._energyBroken)return;this._energy=t;let r=i=>{let s=le(i,de(this.hass?.locale,this.hass?.config?.time_zone));s&&(s.start!==this._period?.start||s.end!==this._period?.end)&&(this._customOpen=!1,this._period=s)};r(t);try{this._unsubEnergy=t.subscribe(r)}catch{this._energy=void 0,this._energyBroken=t}}_detachEnergy(){try{this._unsubEnergy?.()}catch{}this._unsubEnergy=void 0,this._energy=void 0}updated(t){super.updated(t),this._observeControls(),!(!this.hass||!this._period)&&(t.has("_period")||t.has("hass")&&t.get("hass")===void 0?this._load():t.has("_groupingChoice")&&this._loadReport())}_load(){return this._loadCompare(),this._loadReport()}async _loadCompare(){let t=this.hass,r=this._period;if(!t||!r)return;let i=++this._compareSeq;this._compareLoading=!0;try{let s=await $e(t,{period:r,entities:this._config?.entities,timeZone:this._timeZone});if(i!==this._compareSeq)return;this._compare=s,this._compareError=void 0,this._compareHidden=!1}catch(s){if(i!==this._compareSeq)return;if(this._compare=void 0,pt(s)==="unknown_command"){this._compareHidden=!0,this._compareError=void 0;return}this._compareHidden=!1,this._compareError=this._strings.t("compare.error",{message:this._errorMessage(s)})}finally{i===this._compareSeq&&(this._compareLoading=!1)}}_errorMessage(t){let r=pt(t),s=r?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_tariff:"error.unknown_tariff"}[r]:void 0;return s?this._strings.t(s):Mt(t)}async _loadReport(){let t=this.hass,r=this._period;if(!t||!r)return;let i=++this._requestSeq,s=this._timeZone;this._loading=!0;try{let a=await be(t,{period:r,grouping:this.grouping,entities:this._config?.entities,timeZone:s});if(i!==this._requestSeq)return;this._report=a,this._error=void 0,this._reportTimeZone=a.time_zone,this._lastRequestOpen=ot(r,a.time_zone)!==F(r),a.time_zone!==s&&st(r,S(a.time_zone))&&this._load()}catch(a){if(i!==this._requestSeq)return;let d=pt(a),o=d?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_command:"error.unknown_command"}[d]:void 0;this._error=o?this._strings.t(o):this._strings.t("error.generic",{message:Mt(a)}),this._report=void 0}finally{i===this._requestSeq&&(this._loading=!1)}}_selectedPreset(){if(!this._period)return"";let t=this._today(),r=this._period;return K.find(i=>{let s=x(i,t);return s.start===r.start&&s.end===r.end})??""}_onPreset(t){let r=t.target.value;if(r==="custom"){this._openCustom();return}K.includes(r)&&(this._customOpen=!1,this._period=x(r,this._today()))}_openCustom(){this._customOpen=!0,this._customStart=this._period?.start??this._today(),this._customEnd=this._period?.end??this._today()}_applyCustom(){let t=this._customStart,r=this._customEnd;!Et(t)||!Et(r)||(this._period=t<=r?{start:t,end:r}:{start:r,end:t},this._customOpen=!1)}_shift(t){this._period&&(this._period=Tt(this._period,t))}_now(){this._period&&(this._period=se(this._period,this._today()))}_onGrouping(t){this._groupingChoice=t.target.value}render(){if(!this._config||!this.hass||!this._period)return p;let t=this._strings,r=this._config.title??t.t("title");return h`
      <ha-card>
        ${r||this._loading?h`<div class="header">
              ${r?h`<div class="title">${r}</div>`:p}
              ${this._loading?h`<div class="loading" role="status">${t.t("loading")}</div>`:p}
            </div>`:p}
        <div class="controls">
          ${this._energy?this._renderFollowedPeriod(t):h`${this._config.period_source==="energy"?h`<div class="note warning">${t.t("energy_picker_missing")}</div>`:p}${this._renderPicker(t)}`}
        </div>
        <div class="content">
          ${this._error?h`<div class="error" role="alert">${this._error}</div>`:this._report?this._renderReport(t,this._report):p}
        </div>
      </ha-card>
    `}_renderFollowedPeriod(t){return h`
      <div class="picker followed">
        <span class="label" title=${t.t("energy_picker_followed")}>
          ${t.periodLabel(this._period)}
        </span>
        <button
          class="icon refresh"
          title=${t.t("refresh")}
          aria-label=${t.t("refresh")}
          @click=${()=>{this._load()}}
        >
          ${ht(ke)}
        </button>
      </div>
    `}_renderPicker(t){let r=this._period,i=this._selectedPreset(),s=this._today(),a=st(r,s),d=Tt(r,1).start>s;return h`
      <div class="picker">
        <select
          class="preset"
          aria-label=${t.t("period")}
          .value=${nt(i)}
          @change=${this._onPreset}
        >
          <option value="" ?hidden=${i!==""} ?selected=${i===""}>
            ${t.t("custom")}
          </option>
          ${K.map(c=>h`<option value=${c} ?selected=${c===i}>${t.preset(c)}</option>`)}
          <option value="custom">${t.t("custom")}…</option>
        </select>
        <div class="nav">
          <button
            class="icon prev"
            title=${t.t("previous")}
            aria-label=${t.t("previous")}
            @click=${()=>this._shift(-1)}
          >
            ${ht(Qe)}
          </button>
          <button class="label" title=${t.t("custom")} @click=${this._openCustom}>
            ${t.periodLabel(r)}
          </button>
          <button
            class="icon next"
            title=${t.t("next")}
            aria-label=${t.t("next")}
            ?disabled=${d}
            @click=${()=>this._shift(1)}
          >
            ${ht(Je)}
          </button>
          <button class="text now" ?disabled=${a} @click=${this._now}>
            ${t.t("now")}
          </button>
        </div>
        <button
          class="icon refresh"
          title=${t.t("refresh")}
          aria-label=${t.t("refresh")}
          @click=${()=>{this._load()}}
        >
          ${ht(ke)}
        </button>
      </div>
      ${this._customOpen?h`<div class="custom">
            <label
              >${t.t("from")}
              <input
                type="date"
                class="custom-start"
                .value=${this._customStart}
                max=${s}
                @change=${c=>{this._customStart=c.target.value}}
            /></label>
            <label
              >${t.t("to")}
              <input
                type="date"
                class="custom-end"
                .value=${this._customEnd}
                @change=${c=>{this._customEnd=c.target.value}}
            /></label>
            <button class="text apply" @click=${this._applyCustom}>${t.t("apply")}</button>
          </div>`:p}
    `}_activeSort(t){let r=this._config,i=r?.sort?{sort:r.sort,direction:r.sort_direction??ut(r.sort)}:r?.sort_direction?{sort:lt.sort,direction:r.sort_direction}:void 0,s=this._sortChoice??i??lt;return ge(s,t.zones.map(a=>a.key))}_onSort(t){if(!this._report)return;let r=this._activeSort(this._report),i=r.sort===t?r.direction==="asc"?"desc":"asc":ut(t);this._sortChoice={sort:t,direction:i},ye(this._storageKey,this._sortChoice)}_renderReport(t,r){if(r.devices.length===0)return h`<div class="note">${t.t("no_devices")}</div>`;let i=new Map(r.devices.map(d=>[d.entity_id,d])),s=r.totals,a=r.plans.length===0;return h`
      ${a?h`<div class="note warning">${t.t("no_plan")}</div>`:p}
      ${!a&&r.unpriced_hours>0?h`<div class="note warning">
            ${t.t("unpriced",{hours:r.unpriced_hours})}
          </div>`:p}
      <div class="table-wrap">
        <table class="devices">
          ${this._renderHead(t,r,t.t("device"),s,this._activeSort(r))}
          <tbody>
            ${this._deviceRows(r).map(({row:d,depth:c})=>{let o=d.entity_id?i.get(d.entity_id):void 0,l=o?.name??d.entity_id??"",u=o&&o.statistics!=="ok"?t.t(`statistics.${o.statistics}`):"",g=o?.upstream?i.get(o.upstream):void 0;return this._renderRow(t,r,d,l,u,{depth:c,title:c>0&&g?`${l} — ${t.t("nested.title",{name:g.name})}`:l})})}
          </tbody>
          <tfoot>
            ${this._renderRow(t,r,s.total,t.t("total"),"")}
          </tfoot>
        </table>
      </div>
      ${r.devices.some(d=>d.upstream&&i.has(d.upstream))?h`<div class="note nested-note">${t.t("nested.note")}</div>`:p}
      ${this._renderComparison(t,r)}
      ${r.grouping!=="total"?this._renderBreakdown(t,r):p}
      ${r.issues.length>0?this._renderIssues(t,r,i):p}
    `}_deviceRows(t){let r=new Map(t.totals.rows.map(o=>[o.entity_id,o])),i=new Map;for(let o of t.totals.rows)o.entity_id&&i.set(o.entity_id,o);let s=new Map(t.devices.map(o=>[o.entity_id,o.name])),a=me(this._activeSort(t),i,s,this._strings.locale),d=[],c=new Set;for(let{entity_id:o,depth:l}of pe(t.devices,a)){let u=r.get(o);u&&!c.has(u)&&(c.add(u),d.push({row:u,depth:l}))}for(let o of t.totals.rows)c.has(o)||d.push({row:o,depth:0});return d}_renderComparison(t,r){if(this._compareHidden)return p;let i=this._compare,s=this._compareError;if(!i&&!s)return p;let a=r.currency,d=p;if(s)d=h`<div class="error" role="alert">${s}</div>`;else if(i&&i.tariffs.length===0)d=h`<div class="note">${t.t("compare.empty")}</div>`;else if(i){let o=i.actual,l=o.totals.total,u=o.plans.map(g=>g.name).join(" → ");d=h`<div class="table-wrap">
        <table class="comparison">
          <thead>
            <tr>
              <th rowspan="2" class="name">${t.t("compare.tariff")}</th>
              <th rowspan="2" class="num">${t.t("cost")}</th>
              <th colspan="2" class="zone group-start">${t.t("compare.difference")}</th>
              <th rowspan="2" class="num group-start">${t.t("avg_price")}</th>
            </tr>
            <tr>
              <th class="num group-start">${a??""}</th>
              <th class="num">%</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row" class="name" title=${t.t("compare.actual")}>
                <span>${t.t("compare.actual")}</span>
                ${u?h`<span class="sub">${u}</span>`:p}
              </th>
              <td class="num strong">${t.money(l.cost,a)}</td>
              <td class="num group-start">—</td>
              <td class="num">—</td>
              <td class="num group-start">${t.avgPrice(l.cost,l.kwh)}</td>
            </tr>
            ${i.tariffs.map(g=>{let m=g.report.totals.total,b=ue(l.cost,m.cost),G=g.report.unpriced_hours,Nt=G||o.unpriced_hours,xe=t.t(G>0?"compare.unpriced":"compare.unpriced_actual",{hours:Nt});return h`<tr>
                <th scope="row" class="name" title=${g.name}>
                  <span>${g.name}</span>
                  ${Nt>0?h`<span class="badge partial" title=${xe}
                        >!</span
                      >`:p}
                </th>
                <td class="num strong">${t.money(m.cost,a)}</td>
                <td class="num group-start">${t.signedMoney(b.amount,a)}</td>
                <td class="num">${t.signedPercent(b.percent)}</td>
                <td class="num group-start">${t.avgPrice(m.cost,m.kwh)}</td>
              </tr>`})}
          </tbody>
        </table>
      </div>`}let c=this._compareLoading;return h`<section
      class="comparison ${c?"loading":""}"
      aria-busy=${c?"true":"false"}
    >
      <h3>
        ${t.t("compare.title")}
        ${c?h`<span class="loading" role="status">${t.t("loading")}</span>`:p}
      </h3>
      ${d}
    </section>`}_renderHead(t,r,i,s,a){let d=r.currency,c=(l,u,g)=>{if(!a)return g;let m=a.sort===l,b=m?a.direction==="asc"?"desc":"asc":ut(l),G=t.t("sort.by",{column:u,direction:t.t(b==="asc"?"sort.ascending":"sort.descending")});return h`<button
        type="button"
        class="sort"
        data-sort=${l}
        title=${G}
        @click=${()=>this._onSort(l)}
      >
        ${g}${m?h`<span class="sort-indicator" aria-hidden="true"
              >${a.direction==="asc"?"▲":"▼"}</span
            >`:p}
      </button>`},o=l=>a&&a.sort===l?a.direction==="asc"?"ascending":"descending":p;return h`
      <thead>
        <tr>
          <th rowspan="2" class="name" aria-sort=${o("name")}>
            ${c("name",i,i)}
          </th>
          ${r.zones.map((l,u)=>{let g=s.total.zones[u]?.price??null;return h`<th colspan="2" class="zone group-start" aria-sort=${o(l.key)}>
              ${c(l.key,t.t("sort.cost_of",{zone:l.name}),h`${l.name}${g!==null?h`<span class="price">${t.money(g,d)}</span>`:p}`)}
            </th>`})}
          <th colspan="2" class="zone sum group-start" aria-sort=${o("total")}>
            ${c("total",t.t("sort.total_cost"),t.t("total"))}
          </th>
          <th rowspan="2" class="num avg group-start" aria-sort=${o("avg_price")}>
            ${c("avg_price",t.t("avg_price"),t.t("avg_price"))}
          </th>
        </tr>
        <tr>
          ${r.zones.map(()=>h`<th class="num group-start">${t.t("kwh")}</th>
                <th class="num">${t.t("cost")}</th>`)}
          <th class="num group-start">${t.t("kwh")}</th>
          <th class="num">${t.t("cost")}</th>
        </tr>
      </thead>
    `}_renderRow(t,r,i,s,a,d={depth:0,title:s}){let c=r.currency,o=i.coverage,l=t.t("coverage",{measured:o.measured,estimated:o.estimated,excluded:o.excluded,missing:o.missing,expected:o.expected});return h`
      <tr class="status-${i.status} ${d.depth>0?"nested":""}">
        <th
          scope="row"
          class="name"
          title=${d.title}
          style=${d.depth>0?`--depth: ${d.depth}`:p}
        >
          <span>${d.depth>0?"↳ ":""}${s}</span>
          ${i.status!=="complete"?h`<span
                class="badge ${i.status}"
                title="${t.t(`status.${i.status}`)} · ${l}"
                >${i.status==="estimated"?"≈":"!"}</span
              >`:p}
          ${a?h`<span class="sub">${a}</span>`:p}
        </th>
        ${i.zones.map(u=>h`<td class="num group-start">${t.number(u.kwh,2)}</td>
              <td class="num">${t.money(u.cost,c)}</td>`)}
        <td class="num strong group-start">${t.number(i.kwh,2)}</td>
        <td class="num strong">${t.money(i.cost,c)}</td>
        <td class="num group-start">${t.avgPrice(i.cost,i.kwh)}</td>
      </tr>
    `}_renderBreakdown(t,r){let i=this._breakdownEntity,s=i?r.devices.findIndex(o=>o.entity_id===i):-1,a=o=>(s>=0?o.rows.find(l=>l.entity_id===i):void 0)??o.total,d=this._groupingChoice,c=d==="auto"||at(d,this._period)?d:"auto";return h`
      <details class="breakdown" ?open=${this._config?.show_breakdown??!1}>
        <summary>${t.t("breakdown")}</summary>
        <div class="breakdown-controls">
          <label
            >${t.t("breakdown_device")}
            <select
              class="breakdown-device"
              .value=${nt(s>=0?i:"")}
              @change=${o=>{this._breakdownEntity=o.target.value}}
            >
              <option value="">${t.t("all_devices")}</option>
              ${r.devices.map(o=>h`<option value=${o.entity_id} ?selected=${o.entity_id===i}>
                    ${o.name}
                  </option>`)}
            </select>
          </label>
          <label
            >${t.t("grouping")}
            <select class="grouping" .value=${nt(c)} @change=${this._onGrouping}>
              ${we.map(o=>{let l=o==="auto"||at(o,this._period);return h`<option
                  value=${o}
                  ?disabled=${!l}
                  ?selected=${o===c}
                >
                  ${l?t.grouping(o):t.t("grouping.hour_too_long")}
                </option>`})}
            </select>
          </label>
        </div>
        <div class="table-wrap">
          <table class="buckets">
            ${this._renderHead(t,r,t.t("period"),r.totals)}
            <tbody>
              ${r.buckets.map(o=>this._renderRow(t,r,a(o),this._bucketLabel(t,r,o),""))}
            </tbody>
            <tfoot>
              ${this._renderRow(t,r,a(r.totals),t.t("total"),"")}
            </tfoot>
          </table>
        </div>
      </details>
    `}_bucketLabel(t,r,i){if(r.grouping==="week"){let s=i.start.slice(0,10);return t.periodLabel({start:s,end:_(s,6)})}return t.bucketLabel(i.start,r.grouping)}_renderIssues(t,r,i){return h`
      <details class="issues">
        <summary>${t.t("data_quality")} (${r.issues.length})</summary>
        <ul>
          ${r.issues.map(s=>h`<li>
                <span class="who">${i.get(s.entity_id)?.name??s.entity_id}</span>:
                ${t.t(`issue.${s.kind}`)},
                ${t.bucketLabel(s.start,"hour")} – ${t.bucketLabel(s.end,"hour")}
                (${s.hours} h, ${t.number(s.kwh,3)} ${t.t("kwh")})
              </li>`)}
        </ul>
      </details>
    `}static{this.styles=H`
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
  `}};var Lt="energy-cost-stats-panel",Xe="M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",mt=class extends ${constructor(){super(...arguments);this.narrow=!1;this._cardKey="";this._pickerRequested=!1;this._pickerSettled=!1;this._collectionKey="energy_energy_cost_stats_panel"}static{this.properties={hass:{attribute:!1,noAccessor:!0},narrow:{type:Boolean},route:{attribute:!1},panel:{attribute:!1},_error:{state:!0}}}get hass(){return this._hass}set hass(t){let r=this._hass;this._hass=t,this._card&&(this._card.hass=t),this._picker&&(this._picker.hass=t),ct(t,r)&&this.requestUpdate("hass",r)}connectedCallback(){super.connectedCallback(),typeof ResizeObserver<"u"&&(this._pickerObserver=new ResizeObserver(t=>{let r=t[t.length-1];if(!r)return;let i=r.target.getBoundingClientRect().height;this.style.setProperty("--ecs-panel-picker-height",`${Math.ceil(i)}px`)})),this._createPicker(),this._picker&&this.requestUpdate()}disconnectedCallback(){super.disconnectedCallback(),this._pickerObserver?.disconnect(),this._pickerObserver=void 0,this._observedPicker=void 0}async _createPicker(){if(!this._pickerRequested){this._pickerRequested=!0;try{let t=window.loadCardHelpers;if(typeof t!="function")return;let i=(await t.call(window)).createCardElement({type:"energy-date-selection",collection_key:this._collectionKey});if(!i||i.tagName.toLowerCase()==="hui-error-card")return;i.hass=this._hass,this._picker=i,this.setAttribute("has-picker","")}catch{}finally{this._pickerSettled=!0,this.requestUpdate()}}}updated(t){let r=this.shadowRoot?.querySelector(".picker")??void 0;r===this._observedPicker||!this._pickerObserver||(this._observedPicker&&this._pickerObserver.unobserve(this._observedPicker),this._observedPicker=r,r&&this._pickerObserver.observe(r))}willUpdate(t){if(!this._pickerSettled)return;let r={title:"",...this.panel?.config?.card??{},type:`custom:${v}`};this._picker&&(r.period_source="energy",r.collection_key=this._collectionKey);let i=JSON.stringify(r);if(!(i===this._cardKey&&(this._card||this._error))){this._cardKey=i;try{let s=document.createElement(v);s.setConfig(r),s.hass=this._hass,this._card=s,this._error=void 0}catch(s){this._card=void 0,this._error=s instanceof Error?s.message:String(s)}}}_toggleMenu(){this.dispatchEvent(new Event("hass-toggle-menu",{bubbles:!0,composed:!0}))}render(){let t=new O(this._hass?.locale?.language??this._hass?.language);return h`
      <div class="toolbar">
        ${this.narrow?h`<button class="menu" aria-label=${t.t("menu")} @click=${this._toggleMenu}>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d=${Xe}></path></svg>
            </button>`:p}
        <div class="title">${this.panel?.title??""}</div>
      </div>
      ${this._picker?h`<div class="picker">${this._picker}</div>`:p}
      <div class="content ${this.narrow?"narrow":""}">
        ${this._error?h`<div class="error" role="alert">${this._error}</div>`:this._card}
      </div>
    `}static{this.styles=H`
    :host {
      display: block;
      min-height: 100vh;
      /* The card's period controls stick directly under the panel bar. */
      --energy-cost-stats-sticky-top: var(--header-height, 56px);
      background: var(--primary-background-color);
      color: var(--primary-text-color);
    }
    :host([has-picker]) {
      --energy-cost-stats-sticky-top: calc(
        var(--header-height, 56px) + var(--ecs-panel-picker-height, 0px)
      );
    }
    .picker {
      position: sticky;
      top: var(--header-height, 56px);
      z-index: 4;
      background: var(--primary-background-color);
      border-bottom: 1px solid var(--divider-color);
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
  `}};var tr=3e4;function Ot(){let n=window.customElements;n.get(v)||(n.define(v,gt),window.customCards=window.customCards??[],window.customCards.some(e=>e.type===v)||window.customCards.push({type:v,name:"Energy Cost Stats",description:"Electricity cost per device, split by tariff zones",preview:!1})),n.get(Lt)||n.define(Lt,mt)}function er(){document.querySelector("home-assistant")!==null&&!window.customElements.get("home-assistant")?(window.customElements.whenDefined("home-assistant").then(Ot),setTimeout(()=>{window.customElements.get(v)||(console.warn(`${v}: the frontend did not boot in time; defining the card anyway`),Ot())},tr)):Ot()}er();export{tr as BOOT_TIMEOUT_MS,Ot as defineCard,er as registerCard};
