var q=globalThis,B=q.ShadowRoot&&(q.ShadyCSS===void 0||q.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,Y=Symbol(),$t=new WeakMap,R=class{constructor(t,e,s){if(this._$cssResult$=!0,s!==Y)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(B&&t===void 0){let s=e!==void 0&&e.length===1;s&&(t=$t.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),s&&$t.set(e,t))}return t}toString(){return this.cssText}},yt=r=>new R(typeof r=="string"?r:r+"",void 0,Y),Z=(r,...t)=>{let e=r.length===1?r[0]:t.reduce((s,n,i)=>s+(o=>{if(o._$cssResult$===!0)return o.cssText;if(typeof o=="number")return o;throw Error("Value passed to 'css' function must be a 'css' function result: "+o+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(n)+r[i+1],r[0]);return new R(e,r,Y)},vt=(r,t)=>{if(B)r.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let s=document.createElement("style"),n=q.litNonce;n!==void 0&&s.setAttribute("nonce",n),s.textContent=e.cssText,r.appendChild(s)}},Q=B?r=>r:r=>r instanceof CSSStyleSheet?(t=>{let e="";for(let s of t.cssRules)e+=s.cssText;return yt(e)})(r):r;var{is:Gt,defineProperty:Kt,getOwnPropertyDescriptor:jt,getOwnPropertyNames:Vt,getOwnPropertySymbols:Wt,getPrototypeOf:Yt}=Object,F=globalThis,bt=F.trustedTypes,Zt=bt?bt.emptyScript:"",Qt=F.reactiveElementPolyfillSupport,D=(r,t)=>r,J={toAttribute(r,t){switch(t){case Boolean:r=r?Zt:null;break;case Object:case Array:r=r==null?r:JSON.stringify(r)}return r},fromAttribute(r,t){let e=r;switch(t){case Boolean:e=r!==null;break;case Number:e=r===null?null:Number(r);break;case Object:case Array:try{e=JSON.parse(r)}catch{e=null}}return e}},xt=(r,t)=>!Gt(r,t),wt={attribute:!0,type:String,converter:J,reflect:!1,useDefault:!1,hasChanged:xt};Symbol.metadata??=Symbol("metadata"),F.litPropertyMetadata??=new WeakMap;var f=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=wt){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let s=Symbol(),n=this.getPropertyDescriptor(t,s,e);n!==void 0&&Kt(this.prototype,t,n)}}static getPropertyDescriptor(t,e,s){let{get:n,set:i}=jt(this.prototype,t)??{get(){return this[e]},set(o){this[e]=o}};return{get:n,set(o){let d=n?.call(this);i?.call(this,o),this.requestUpdate(t,d,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??wt}static _$Ei(){if(this.hasOwnProperty(D("elementProperties")))return;let t=Yt(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(D("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(D("properties"))){let e=this.properties,s=[...Vt(e),...Wt(e)];for(let n of s)this.createProperty(n,e[n])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[s,n]of e)this.elementProperties.set(s,n)}this._$Eh=new Map;for(let[e,s]of this.elementProperties){let n=this._$Eu(e,s);n!==void 0&&this._$Eh.set(n,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let s=new Set(t.flat(1/0).reverse());for(let n of s)e.unshift(Q(n))}else t!==void 0&&e.push(Q(t));return e}static _$Eu(t,e){let s=e.attribute;return s===!1?void 0:typeof s=="string"?s:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return vt(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){let s=this.constructor.elementProperties.get(t),n=this.constructor._$Eu(t,s);if(n!==void 0&&s.reflect===!0){let i=(s.converter?.toAttribute!==void 0?s.converter:J).toAttribute(e,s.type);this._$Em=t,i==null?this.removeAttribute(n):this.setAttribute(n,i),this._$Em=null}}_$AK(t,e){let s=this.constructor,n=s._$Eh.get(t);if(n!==void 0&&this._$Em!==n){let i=s.getPropertyOptions(n),o=typeof i.converter=="function"?{fromAttribute:i.converter}:i.converter?.fromAttribute!==void 0?i.converter:J;this._$Em=n;let d=o.fromAttribute(e,i.type);this[n]=d??this._$Ej?.get(n)??d,this._$Em=null}}requestUpdate(t,e,s,n=!1,i){if(t!==void 0){let o=this.constructor;if(n===!1&&(i=this[t]),s??=o.getPropertyOptions(t),!((s.hasChanged??xt)(i,e)||s.useDefault&&s.reflect&&i===this._$Ej?.get(t)&&!this.hasAttribute(o._$Eu(t,s))))return;this.C(t,e,s)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:n,wrapped:i},o){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,o??e??this[t]),i!==!0||o!==void 0)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),n===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[n,i]of this._$Ep)this[n]=i;this._$Ep=void 0}let s=this.constructor.elementProperties;if(s.size>0)for(let[n,i]of s){let{wrapped:o}=i,d=this[n];o!==!0||this._$AL.has(n)||d===void 0||this.C(n,void 0,i,d)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(s=>s.hostUpdate?.()),this.update(e)):this._$EM()}catch(s){throw t=!1,this._$EM(),s}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};f.elementStyles=[],f.shadowRootOptions={mode:"open"},f[D("elementProperties")]=new Map,f[D("finalized")]=new Map,Qt?.({ReactiveElement:f}),(F.reactiveElementVersions??=[]).push("2.1.2");var it=globalThis,St=r=>r,G=it.trustedTypes,At=G?G.createPolicy("lit-html",{createHTML:r=>r}):void 0,Rt="$lit$",v=`lit$${Math.random().toFixed(9).slice(2)}$`,Dt="?"+v,Jt=`<${Dt}>`,S=document,M=()=>S.createComment(""),L=r=>r===null||typeof r!="object"&&typeof r!="function",ot=Array.isArray,Xt=r=>ot(r)||typeof r?.[Symbol.iterator]=="function",X=`[ 	
\f\r]`,U=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,kt=/-->/g,Ct=/>/g,w=RegExp(`>|${X}(?:([^\\s"'>=/]+)(${X}*=${X}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Et=/'/g,Pt=/"/g,Ut=/^(?:script|style|textarea|title)$/i,at=r=>(t,...e)=>({_$litType$:r,strings:t,values:e}),u=at(1),fe=at(2),$e=at(3),A=Symbol.for("lit-noChange"),c=Symbol.for("lit-nothing"),Tt=new WeakMap,x=S.createTreeWalker(S,129);function Mt(r,t){if(!ot(r)||!r.hasOwnProperty("raw"))throw Error("invalid template strings array");return At!==void 0?At.createHTML(t):t}var te=(r,t)=>{let e=r.length-1,s=[],n,i=t===2?"<svg>":t===3?"<math>":"",o=U;for(let d=0;d<e;d++){let a=r[d],l,p,h=-1,_=0;for(;_<a.length&&(o.lastIndex=_,p=o.exec(a),p!==null);)_=o.lastIndex,o===U?p[1]==="!--"?o=kt:p[1]!==void 0?o=Ct:p[2]!==void 0?(Ut.test(p[2])&&(n=RegExp("</"+p[2],"g")),o=w):p[3]!==void 0&&(o=w):o===w?p[0]===">"?(o=n??U,h=-1):p[1]===void 0?h=-2:(h=o.lastIndex-p[2].length,l=p[1],o=p[3]===void 0?w:p[3]==='"'?Pt:Et):o===Pt||o===Et?o=w:o===kt||o===Ct?o=U:(o=w,n=void 0);let y=o===w&&r[d+1].startsWith("/>")?" ":"";i+=o===U?a+Jt:h>=0?(s.push(l),a.slice(0,h)+Rt+a.slice(h)+v+y):a+v+(h===-2?d:y)}return[Mt(r,i+(r[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),s]},N=class r{constructor({strings:t,_$litType$:e},s){let n;this.parts=[];let i=0,o=0,d=t.length-1,a=this.parts,[l,p]=te(t,e);if(this.el=r.createElement(l,s),x.currentNode=this.el.content,e===2||e===3){let h=this.el.content.firstChild;h.replaceWith(...h.childNodes)}for(;(n=x.nextNode())!==null&&a.length<d;){if(n.nodeType===1){if(n.hasAttributes())for(let h of n.getAttributeNames())if(h.endsWith(Rt)){let _=p[o++],y=n.getAttribute(h).split(v),z=/([.?@])?(.*)/.exec(_);a.push({type:1,index:i,name:z[2],strings:y,ctor:z[1]==="."?et:z[1]==="?"?st:z[1]==="@"?rt:E}),n.removeAttribute(h)}else h.startsWith(v)&&(a.push({type:6,index:i}),n.removeAttribute(h));if(Ut.test(n.tagName)){let h=n.textContent.split(v),_=h.length-1;if(_>0){n.textContent=G?G.emptyScript:"";for(let y=0;y<_;y++)n.append(h[y],M()),x.nextNode(),a.push({type:2,index:++i});n.append(h[_],M())}}}else if(n.nodeType===8)if(n.data===Dt)a.push({type:2,index:i});else{let h=-1;for(;(h=n.data.indexOf(v,h+1))!==-1;)a.push({type:7,index:i}),h+=v.length-1}i++}}static createElement(t,e){let s=S.createElement("template");return s.innerHTML=t,s}};function C(r,t,e=r,s){if(t===A)return t;let n=s!==void 0?e._$Co?.[s]:e._$Cl,i=L(t)?void 0:t._$litDirective$;return n?.constructor!==i&&(n?._$AO?.(!1),i===void 0?n=void 0:(n=new i(r),n._$AT(r,e,s)),s!==void 0?(e._$Co??=[])[s]=n:e._$Cl=n),n!==void 0&&(t=C(r,n._$AS(r,t.values),n,s)),t}var tt=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:s}=this._$AD,n=(t?.creationScope??S).importNode(e,!0);x.currentNode=n;let i=x.nextNode(),o=0,d=0,a=s[0];for(;a!==void 0;){if(o===a.index){let l;a.type===2?l=new H(i,i.nextSibling,this,t):a.type===1?l=new a.ctor(i,a.name,a.strings,this,t):a.type===6&&(l=new nt(i,this,t)),this._$AV.push(l),a=s[++d]}o!==a?.index&&(i=x.nextNode(),o++)}return x.currentNode=S,n}p(t){let e=0;for(let s of this._$AV)s!==void 0&&(s.strings!==void 0?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}},H=class r{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,n){this.type=2,this._$AH=c,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=n,this._$Cv=n?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=C(this,t,e),L(t)?t===c||t==null||t===""?(this._$AH!==c&&this._$AR(),this._$AH=c):t!==this._$AH&&t!==A&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):Xt(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==c&&L(this._$AH)?this._$AA.nextSibling.data=t:this.T(S.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:s}=t,n=typeof s=="number"?this._$AC(t):(s.el===void 0&&(s.el=N.createElement(Mt(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===n)this._$AH.p(e);else{let i=new tt(n,this),o=i.u(this.options);i.p(e),this.T(o),this._$AH=i}}_$AC(t){let e=Tt.get(t.strings);return e===void 0&&Tt.set(t.strings,e=new N(t)),e}k(t){ot(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,s,n=0;for(let i of t)n===e.length?e.push(s=new r(this.O(M()),this.O(M()),this,this.options)):s=e[n],s._$AI(i),n++;n<e.length&&(this._$AR(s&&s._$AB.nextSibling,n),e.length=n)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let s=St(t).nextSibling;St(t).remove(),t=s}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},E=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,n,i){this.type=1,this._$AH=c,this._$AN=void 0,this.element=t,this.name=e,this._$AM=n,this.options=i,s.length>2||s[0]!==""||s[1]!==""?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=c}_$AI(t,e=this,s,n){let i=this.strings,o=!1;if(i===void 0)t=C(this,t,e,0),o=!L(t)||t!==this._$AH&&t!==A,o&&(this._$AH=t);else{let d=t,a,l;for(t=i[0],a=0;a<i.length-1;a++)l=C(this,d[s+a],e,a),l===A&&(l=this._$AH[a]),o||=!L(l)||l!==this._$AH[a],l===c?t=c:t!==c&&(t+=(l??"")+i[a+1]),this._$AH[a]=l}o&&!n&&this.j(t)}j(t){t===c?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},et=class extends E{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===c?void 0:t}},st=class extends E{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==c)}},rt=class extends E{constructor(t,e,s,n,i){super(t,e,s,n,i),this.type=5}_$AI(t,e=this){if((t=C(this,t,e,0)??c)===A)return;let s=this._$AH,n=t===c&&s!==c||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,i=t!==c&&(s===c||n);n&&this.element.removeEventListener(this.name,this,s),i&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},nt=class{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){C(this,t)}};var ee=it.litHtmlPolyfillSupport;ee?.(N,H),(it.litHtmlVersions??=[]).push("3.3.3");var Lt=(r,t,e)=>{let s=e?.renderBefore??t,n=s._$litPart$;if(n===void 0){let i=e?.renderBefore??null;s._$litPart$=n=new H(t.insertBefore(M(),i),i,void 0,e??{})}return n._$AI(r),n};var dt=globalThis,b=class extends f{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=Lt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return A}};b._$litElement$=!0,b.finalized=!0,dt.litElementHydrateSupport?.({LitElement:b});var se=dt.litElementPolyfillSupport;se?.({LitElement:b});(dt.litElementVersions??=[]).push("4.2.2");var O=["today","yesterday","this_week","last_week","this_month","last_month","this_quarter","this_year","now-7d","now-30d","now-12m"];function m(r){let t=/^(\d{4})-(\d{2})-(\d{2})$/.exec(r);if(!t)throw new Error(`invalid date: ${r}`);let[,e,s,n]=t;return new Date(Date.UTC(Number(e),Number(s)-1,Number(n)))}function K(r){return r.toISOString().slice(0,10)}function ut(r){try{return K(m(r))===r}catch{return!1}}function g(r,t){return K(new Date(m(r).getTime()+t*864e5))}function P(r,t=0){let e=m(r);return K(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t,1)))}function k(r,t=0){let e=m(r);return K(new Date(Date.UTC(e.getUTCFullYear(),e.getUTCMonth()+t+1,0)))}function lt(r){let t=(m(r).getUTCDay()+6)%7;return g(r,-t)}function I(r){return Math.round((m(r.end).getTime()-m(r.start).getTime())/864e5)+1}function ht(r){let t=m(r.start);if(t.getUTCDate()!==1||k(r.end)!==r.end)return null;let e=m(r.end);return(e.getUTCFullYear()-t.getUTCFullYear())*12+(e.getUTCMonth()-t.getUTCMonth())+1}function pt(r,t=new Date){let e={year:"numeric",month:"2-digit",day:"2-digit"},s;try{s=new Intl.DateTimeFormat("en-CA",{...e,timeZone:r}).formatToParts(t)}catch{s=new Intl.DateTimeFormat("en-CA",e).formatToParts(t)}let n=i=>s.find(o=>o.type===i)?.value??"";return`${n("year")}-${n("month")}-${n("day")}`}function $(r,t){switch(r){case"today":return{start:t,end:t};case"yesterday":{let e=g(t,-1);return{start:e,end:e}}case"this_week":{let e=lt(t);return{start:e,end:g(e,6)}}case"last_week":{let e=g(lt(t),-7);return{start:e,end:g(e,6)}}case"this_month":return{start:P(t),end:k(t)};case"last_month":return{start:P(t,-1),end:k(t,-1)};case"this_quarter":{let e=m(t).getUTCMonth(),s=P(t,-(e%3));return{start:s,end:k(s,2)}}case"this_year":{let e=t.slice(0,4);return{start:`${e}-01-01`,end:`${e}-12-31`}}case"now-7d":return{start:g(t,-6),end:t};case"now-30d":return{start:g(t,-29),end:t};case"now-12m":return{start:P(t,-11),end:k(t)}}}function gt(r){let t=ht(r);if(t!==null){let s=m(r.start).getUTCMonth();return t===1?"month":t===3&&s%3===0?"quarter":t===12&&s===0?"year":"months"}let e=I(r);return e===1?"day":e===7&&lt(r.start)===r.start?"week":"days"}function mt(r,t){let e=ht(r);if(e!==null){let n=e*t;return{start:P(r.start,n),end:k(r.end,n)}}let s=I(r)*t;return{start:g(r.start,s),end:g(r.end,s)}}function Nt(r,t){switch(gt(r)){case"day":return $("today",t);case"week":return $("this_week",t);case"month":return $("this_month",t);case"quarter":return $("this_quarter",t);case"year":return $("this_year",t);case"months":{let s=ht(r)??1;return{start:P(t,-(s-1)),end:k(t)}}case"days":return{start:g(t,-(I(r)-1)),end:t}}}function j(r,t){return r.start<=t&&t<=r.end}function ct(r){return g(r.end,1)}function Ht(r,t,e=new Date){let s=pt(t,e);if(!j(r,s))return ct(r);let n;try{n=new Intl.DateTimeFormat("en-GB",{timeZone:t,hour:"2-digit",minute:"2-digit",hourCycle:"h23"}).formatToParts(e)}catch{return ct(r)}let i=Number(n.find(a=>a.type==="hour")?.value),o=Number(n.find(a=>a.type==="minute")?.value);if(!Number.isFinite(i)||o!==e.getUTCMinutes())return ct(r);let d=r.start===s?Math.max(i,1):i;return`${s}T${String(d).padStart(2,"0")}:00:00`}var re=31;function Ot(r){let t=I(r);return t<=2?"hour":t<=45?"day":t<=120?"week":"month"}function _t(r,t){return r!=="hour"||I(t)<=re}var ne={title:"Energy cost",previous:"Previous",next:"Next",now:"Now",refresh:"Refresh",period:"Period",custom:"Custom period",from:"From",to:"To",apply:"Apply",grouping:"Grouping","grouping.auto":"Auto","grouping.hour":"Hours","grouping.day":"Days","grouping.week":"Weeks","grouping.month":"Months","grouping.hour_too_long":"Hours: up to 31 days","preset.today":"Today","preset.yesterday":"Yesterday","preset.this_week":"This week","preset.last_week":"Last week","preset.this_month":"This month","preset.last_month":"Last month","preset.this_quarter":"This quarter","preset.this_year":"This year","preset.now-7d":"Last 7 days","preset.now-30d":"Last 30 days","preset.now-12m":"Last 12 months",device:"Device",total:"Total",kwh:"kWh",cost:"Cost",avg_price:"Avg. price",breakdown:"By period",breakdown_device:"Show",all_devices:"All devices",data_quality:"Data quality",loading:"Loading…",no_devices:"No energy sensors selected. Add them in the integration options.",no_plan:"No tariff plan covers this period: costs are unknown.",unpriced:"{hours} h before the first tariff plan are not priced.","status.complete":"Complete","status.estimated":"Contains estimated hours (spread over a data gap)","status.partial":"Some hours are missing","status.missing":"No data","issue.estimated":"estimated","issue.excluded_negative":"excluded (negative)","issue.excluded_spike":"excluded (spike)","statistics.no_statistics":"no statistics yet","statistics.unsupported":"unsupported sensor","error.not_loaded":"Energy Cost Stats is not set up or not loaded.","error.invalid_period":"Invalid period.","error.period_too_long":"The period is too long for this grouping.","error.unknown_entity":"The card lists a sensor that is not selected in the integration.","error.unknown_command":"The integration is not loaded (restart Home Assistant after installing).","error.generic":"Could not load the report: {message}",coverage:"{measured} measured, {estimated} estimated, {excluded} excluded, {missing} missing of {expected} h"},ie={title:"Стоимость электроэнергии",previous:"Назад",next:"Вперёд",now:"Сейчас",refresh:"Обновить",period:"Период",custom:"Свой период",from:"С",to:"По",apply:"Применить",grouping:"Группировка","grouping.auto":"Авто","grouping.hour":"По часам","grouping.day":"По дням","grouping.week":"По неделям","grouping.month":"По месяцам","grouping.hour_too_long":"По часам: до 31 дня","preset.today":"Сегодня","preset.yesterday":"Вчера","preset.this_week":"Эта неделя","preset.last_week":"Прошлая неделя","preset.this_month":"Этот месяц","preset.last_month":"Прошлый месяц","preset.this_quarter":"Этот квартал","preset.this_year":"Этот год","preset.now-7d":"Последние 7 дней","preset.now-30d":"Последние 30 дней","preset.now-12m":"Последние 12 месяцев",device:"Устройство",total:"Итого",kwh:"кВт·ч",cost:"Сумма",avg_price:"Ср. цена",breakdown:"По периодам",breakdown_device:"Показать",all_devices:"Все устройства",data_quality:"Качество данных",loading:"Загрузка…",no_devices:"Не выбраны датчики энергии. Добавьте их в настройках интеграции.",no_plan:"Для этого периода нет тарифного плана: стоимость неизвестна.",unpriced:"{hours} ч до первого тарифного плана не оценены.","status.complete":"Полные данные","status.estimated":"Есть оценочные часы (распределены по пропуску)","status.partial":"Часть часов отсутствует","status.missing":"Нет данных","issue.estimated":"оценка","issue.excluded_negative":"исключено (отрицательное)","issue.excluded_spike":"исключено (выброс)","statistics.no_statistics":"статистики пока нет","statistics.unsupported":"датчик не поддерживается","error.not_loaded":"Energy Cost Stats не настроена или не загружена.","error.invalid_period":"Неверный период.","error.period_too_long":"Период слишком длинный для этой группировки.","error.unknown_entity":"В карточке указан датчик, не выбранный в интеграции.","error.unknown_command":"Интеграция не загружена (перезапустите Home Assistant после установки).","error.generic":"Не удалось загрузить отчёт: {message}",coverage:"{measured} измерено, {estimated} оценено, {excluded} исключено, {missing} нет из {expected} ч"},V=class{constructor(t){this.locale=t||"en",this.table=this.locale.toLowerCase().startsWith("ru")?ie:ne}t(t,e={}){return this.table[t].replace(/\{(\w+)\}/g,(s,n)=>n in e?String(e[n]):`{${n}}`)}preset(t){return this.t(`preset.${t}`)}grouping(t){return this.t(`grouping.${t}`)}number(t,e){return t==null?"—":new Intl.NumberFormat(this.locale,{minimumFractionDigits:e,maximumFractionDigits:e}).format(Number(t))}money(t,e){if(t==null)return"—";if(e)try{return new Intl.NumberFormat(this.locale,{style:"currency",currency:e,minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(t))}catch{}return this.number(t,2)}avgPrice(t,e){return t===null||e===null||Number(e)===0?"—":this.number(String(Number(t)/Number(e)),2)}date(t,e){return new Intl.DateTimeFormat(this.locale,{...e,timeZone:"UTC"}).format(new Date(`${t}T00:00:00Z`))}periodLabel(t){switch(gt(t)){case"day":return this.date(t.start,{day:"numeric",month:"long",year:"numeric"});case"month":return this.date(t.start,{month:"long",year:"numeric"});case"quarter":return`Q${Math.floor(Number(t.start.slice(5,7))/3)+1} ${t.start.slice(0,4)}`;case"year":return t.start.slice(0,4);case"months":return`${this.date(t.start,{month:"short",year:"numeric"})} – ${this.date(t.end,{month:"short",year:"numeric"})}`;default:{let s=t.start.slice(0,4)===t.end.slice(0,4),n=this.date(t.start,{day:"numeric",month:"short",...s?{}:{year:"numeric"}}),i=this.date(t.end,{day:"numeric",month:"short",year:"numeric"});return`${n} – ${i}`}}}bucketLabel(t,e){let s=t.slice(0,10);switch(e){case"hour":return`${this.date(s,{day:"numeric",month:"short"})} ${t.slice(11,16)}`;case"day":return this.date(s,{weekday:"short",day:"numeric",month:"short"});case"week":return this.date(s,{day:"numeric",month:"short",year:"numeric"});case"month":return this.date(s,{month:"long",year:"numeric"});default:return this.t("total")}}};var oe="energy_cost_stats/report";function ae(r){let t={type:oe,start:r.period.start,end:Ht(r.period,r.timeZone,r.now),grouping:r.grouping};return r.entities&&r.entities.length>0&&(t.entities=r.entities),t}function It(r,t){return r.callWS(ae(t))}function zt(r){if(r&&typeof r=="object"&&"code"in r){let t=r.code;return typeof t=="string"?t:void 0}}function qt(r){return r&&typeof r=="object"&&"message"in r?String(r.message):String(r)}var T="energy-cost-stats-card",Bt=["auto","hour","day","week","month"],de=600*1e3,ce="M15.41,16.58L10.83,12L15.41,7.41L14,6L8,12L14,18L15.41,16.58Z",le="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z",ue="M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z";function ft(r){return u`<svg viewBox="0 0 24 24" aria-hidden="true"><path d=${r}></path></svg>`}var W=class extends b{constructor(){super(...arguments);this._groupingChoice="auto";this._loading=!1;this._customOpen=!1;this._customStart="";this._customEnd="";this._breakdownEntity="";this._requestSeq=0}static{this.properties={hass:{attribute:!1},_config:{state:!0},_period:{state:!0},_groupingChoice:{state:!0},_report:{state:!0},_error:{state:!0},_loading:{state:!0},_customOpen:{state:!0},_customStart:{state:!0},_customEnd:{state:!0},_breakdownEntity:{state:!0}}}static getStubConfig(){return{type:`custom:${T}`,period:"this_month"}}setConfig(e){if(!e||typeof e!="object")throw new Error("Invalid configuration");if(e.period!==void 0&&!O.includes(e.period))throw new Error(`Unknown period: ${String(e.period)}`);if(e.grouping!==void 0&&!Bt.includes(e.grouping))throw new Error(`Unknown grouping: ${String(e.grouping)}`);if(e.entities!==void 0&&(!Array.isArray(e.entities)||e.entities.some(n=>typeof n!="string")))throw new Error("entities must be a list of entity ids");let s=this._config;this._config=e,this._groupingChoice=e.grouping??"auto",s&&this._period&&(this._period=void 0,this._report=void 0)}getCardSize(){return 3+(this._report?.devices.length??2)}get _strings(){return new V(this.hass?.locale?.language??this.hass?.language)}get _timeZone(){return this._report?.time_zone??this.hass?.config?.time_zone}_today(){return pt(this._timeZone)}get grouping(){let e=this._period;if(!e)return"day";let s=this._groupingChoice;return s!=="auto"&&_t(s,e)?s:Ot(e)}connectedCallback(){super.connectedCallback(),this._timer=setInterval(()=>{this._period&&j(this._period,this._today())&&!this._loading&&this._load()},de)}disconnectedCallback(){super.disconnectedCallback(),this._timer!==void 0&&clearInterval(this._timer),this._timer=void 0}willUpdate(e){this.hass&&this._config&&!this._period&&(this._period=$(this._config.period??"this_month",this._today())),super.willUpdate(e)}updated(e){super.updated(e),!(!this.hass||!this._period)&&(e.has("_period")||e.has("_groupingChoice")||e.has("hass")&&e.get("hass")===void 0)&&this._load()}async _load(){let e=this.hass,s=this._period;if(!e||!s)return;let n=++this._requestSeq;this._loading=!0;try{let i=await It(e,{period:s,grouping:this.grouping,entities:this._config?.entities,timeZone:this._timeZone});if(n!==this._requestSeq)return;this._report=i,this._error=void 0}catch(i){if(n!==this._requestSeq)return;let o=zt(i),a=o?{not_loaded:"error.not_loaded",invalid_period:"error.invalid_period",period_too_long:"error.period_too_long",unknown_entity:"error.unknown_entity",unknown_command:"error.unknown_command"}[o]:void 0;this._error=a?this._strings.t(a):this._strings.t("error.generic",{message:qt(i)}),this._report=void 0}finally{n===this._requestSeq&&(this._loading=!1)}}_selectedPreset(){if(!this._period)return"";let e=this._today(),s=this._period;return O.find(n=>{let i=$(n,e);return i.start===s.start&&i.end===s.end})??""}_onPreset(e){let s=e.target.value;if(s==="custom"){this._openCustom();return}O.includes(s)&&(this._customOpen=!1,this._period=$(s,this._today()))}_openCustom(){this._customOpen=!0,this._customStart=this._period?.start??this._today(),this._customEnd=this._period?.end??this._today()}_applyCustom(){let e=this._customStart,s=this._customEnd;!ut(e)||!ut(s)||(this._period=e<=s?{start:e,end:s}:{start:s,end:e},this._customOpen=!1)}_shift(e){this._period&&(this._period=mt(this._period,e))}_now(){this._period&&(this._period=Nt(this._period,this._today()))}_onGrouping(e){this._groupingChoice=e.target.value}render(){if(!this._config||!this.hass||!this._period)return c;let e=this._strings,s=this._config.title??e.t("title");return u`
      <ha-card>
        <div class="header">
          <div class="title">${s}</div>
          ${this._loading?u`<div class="loading" role="status">${e.t("loading")}</div>`:c}
        </div>
        ${this._renderPicker(e)}
        <div class="content">
          ${this._error?u`<div class="error" role="alert">${this._error}</div>`:this._report?this._renderReport(e,this._report):c}
        </div>
      </ha-card>
    `}_renderPicker(e){let s=this._period,n=this._selectedPreset(),i=this._today(),o=j(s,i),d=mt(s,1).start>i;return u`
      <div class="picker">
        <select
          class="preset"
          aria-label=${e.t("period")}
          .value=${n}
          @change=${this._onPreset}
        >
          <option value="" ?hidden=${n!==""} ?selected=${n===""}>
            ${e.t("custom")}
          </option>
          ${O.map(a=>u`<option value=${a} ?selected=${a===n}>${e.preset(a)}</option>`)}
          <option value="custom">${e.t("custom")}…</option>
        </select>
        <div class="nav">
          <button
            class="icon prev"
            title=${e.t("previous")}
            aria-label=${e.t("previous")}
            @click=${()=>this._shift(-1)}
          >
            ${ft(ce)}
          </button>
          <button class="label" title=${e.t("custom")} @click=${this._openCustom}>
            ${e.periodLabel(s)}
          </button>
          <button
            class="icon next"
            title=${e.t("next")}
            aria-label=${e.t("next")}
            ?disabled=${d}
            @click=${()=>this._shift(1)}
          >
            ${ft(le)}
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
          ${ft(ue)}
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
          </div>`:c}
    `}_renderReport(e,s){if(s.devices.length===0)return u`<div class="note">${e.t("no_devices")}</div>`;let n=new Map(s.devices.map(d=>[d.entity_id,d])),i=s.totals,o=s.plans.length===0;return u`
      ${o?u`<div class="note warning">${e.t("no_plan")}</div>`:c}
      ${!o&&s.unpriced_hours>0?u`<div class="note warning">
            ${e.t("unpriced",{hours:s.unpriced_hours})}
          </div>`:c}
      <div class="table-wrap">
        <table class="devices">
          ${this._renderHead(e,s,e.t("device"),i)}
          <tbody>
            ${i.rows.map(d=>{let a=d.entity_id?n.get(d.entity_id):void 0,l=a?.name??d.entity_id??"",p=a&&a.statistics!=="ok"?e.t(`statistics.${a.statistics}`):"";return this._renderRow(e,s,d,l,p)})}
          </tbody>
          <tfoot>
            ${this._renderRow(e,s,i.total,e.t("total"),"")}
          </tfoot>
        </table>
      </div>
      ${s.grouping!=="total"?this._renderBreakdown(e,s):c}
      ${s.issues.length>0?this._renderIssues(e,s,n):c}
    `}_renderHead(e,s,n,i){let o=s.currency;return u`
      <thead>
        <tr>
          <th rowspan="2" class="name">${n}</th>
          ${s.zones.map((d,a)=>{let l=i.total.zones[a]?.price??null;return u`<th colspan="2" class="zone">
              ${d.name}${l!==null?u`<span class="price">${e.money(l,o)}</span>`:c}
            </th>`})}
          <th colspan="3" class="zone sum">${e.t("total")}</th>
        </tr>
        <tr>
          ${s.zones.map(()=>u`<th class="num">${e.t("kwh")}</th><th class="num">${e.t("cost")}</th>`)}
          <th class="num">${e.t("kwh")}</th>
          <th class="num">${e.t("cost")}</th>
          <th class="num">${e.t("avg_price")}</th>
        </tr>
      </thead>
    `}_renderRow(e,s,n,i,o){let d=s.currency,a=n.coverage,l=e.t("coverage",{measured:a.measured,estimated:a.estimated,excluded:a.excluded,missing:a.missing,expected:a.expected});return u`
      <tr class="status-${n.status}">
        <th scope="row" class="name">
          <span>${i}</span>
          ${n.status!=="complete"?u`<span
                class="badge ${n.status}"
                title="${e.t(`status.${n.status}`)} · ${l}"
                >${n.status==="estimated"?"≈":"!"}</span
              >`:c}
          ${o?u`<span class="sub">${o}</span>`:c}
        </th>
        ${n.zones.map(p=>u`<td class="num">${e.number(p.kwh,2)}</td>
              <td class="num">${e.money(p.cost,d)}</td>`)}
        <td class="num strong">${e.number(n.kwh,2)}</td>
        <td class="num strong">${e.money(n.cost,d)}</td>
        <td class="num">${e.avgPrice(n.cost,n.kwh)}</td>
      </tr>
    `}_renderBreakdown(e,s){let n=this._breakdownEntity,i=n?s.devices.findIndex(d=>d.entity_id===n):-1,o=d=>i>=0?d.rows[i]??d.total:d.total;return u`
      <details class="breakdown" ?open=${this._config?.show_breakdown??!1}>
        <summary>${e.t("breakdown")}</summary>
        <div class="breakdown-controls">
          <label
            >${e.t("breakdown_device")}
            <select
              class="breakdown-device"
              .value=${i>=0?n:""}
              @change=${d=>{this._breakdownEntity=d.target.value}}
            >
              <option value="">${e.t("all_devices")}</option>
              ${s.devices.map(d=>u`<option value=${d.entity_id} ?selected=${d.entity_id===n}>
                    ${d.name}
                  </option>`)}
            </select>
          </label>
          <label
            >${e.t("grouping")}
            <select class="grouping" .value=${this._groupingChoice} @change=${this._onGrouping}>
              ${Bt.map(d=>{let a=d==="auto"||_t(d,this._period);return u`<option
                  value=${d}
                  ?disabled=${!a}
                  ?selected=${d===this._groupingChoice}
                >
                  ${a?e.grouping(d):e.t("grouping.hour_too_long")}
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
    `}_bucketLabel(e,s,n){if(s.grouping==="week"){let i=n.start.slice(0,10),o=g(n.end.slice(0,10),-1);return e.periodLabel({start:i,end:o<i?i:o})}return e.bucketLabel(n.start,s.grouping)}_renderIssues(e,s,n){return u`
      <details class="issues">
        <summary>${e.t("data_quality")} (${s.issues.length})</summary>
        <ul>
          ${s.issues.map(i=>u`<li>
                <span class="who">${n.get(i.entity_id)?.name??i.entity_id}</span>:
                ${e.t(`issue.${i.kind}`)},
                ${e.bucketLabel(i.start,"hour")} – ${e.bucketLabel(i.end,"hour")}
                (${i.hours} h, ${e.number(i.kwh,3)} ${e.t("kwh")})
              </li>`)}
        </ul>
      </details>
    `}static{this.styles=Z`
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
  `}};function Ft(){let r=window.customElements;r.get(T)||(r.define(T,W),window.customCards=window.customCards??[],window.customCards.some(t=>t.type===T)||window.customCards.push({type:T,name:"Energy Cost Stats",description:"Electricity cost per device, split by tariff zones",preview:!1}))}function he(){document.querySelector("home-assistant")!==null&&!window.customElements.get("home-assistant")?window.customElements.whenDefined("home-assistant").then(Ft):Ft()}he();export{Ft as defineCard,he as registerCard};
