"use strict";(self.webpackChunkmy_website=self.webpackChunkmy_website||[]).push([[3402],{3905:function(e,n,t){t.d(n,{Zo:function(){return u},kt:function(){return d}});var r=t(7294);function a(e,n,t){return n in e?Object.defineProperty(e,n,{value:t,enumerable:!0,configurable:!0,writable:!0}):e[n]=t,e}function o(e,n){var t=Object.keys(e);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(e);n&&(r=r.filter((function(n){return Object.getOwnPropertyDescriptor(e,n).enumerable}))),t.push.apply(t,r)}return t}function c(e){for(var n=1;n<arguments.length;n++){var t=null!=arguments[n]?arguments[n]:{};n%2?o(Object(t),!0).forEach((function(n){a(e,n,t[n])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(t)):o(Object(t)).forEach((function(n){Object.defineProperty(e,n,Object.getOwnPropertyDescriptor(t,n))}))}return e}function l(e,n){if(null==e)return{};var t,r,a=function(e,n){if(null==e)return{};var t,r,a={},o=Object.keys(e);for(r=0;r<o.length;r++)t=o[r],n.indexOf(t)>=0||(a[t]=e[t]);return a}(e,n);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);for(r=0;r<o.length;r++)t=o[r],n.indexOf(t)>=0||Object.prototype.propertyIsEnumerable.call(e,t)&&(a[t]=e[t])}return a}var i=r.createContext({}),p=function(e){var n=r.useContext(i),t=n;return e&&(t="function"==typeof e?e(n):c(c({},n),e)),t},u=function(e){var n=p(e.components);return r.createElement(i.Provider,{value:n},e.children)},s={inlineCode:"code",wrapper:function(e){var n=e.children;return r.createElement(r.Fragment,{},n)}},m=r.forwardRef((function(e,n){var t=e.components,a=e.mdxType,o=e.originalType,i=e.parentName,u=l(e,["components","mdxType","originalType","parentName"]),m=p(t),d=a,f=m["".concat(i,".").concat(d)]||m[d]||s[d]||o;return t?r.createElement(f,c(c({ref:n},u),{},{components:t})):r.createElement(f,c({ref:n},u))}));function d(e,n){var t=arguments,a=n&&n.mdxType;if("string"==typeof e||a){var o=t.length,c=new Array(o);c[0]=m;var l={};for(var i in n)hasOwnProperty.call(n,i)&&(l[i]=n[i]);l.originalType=e,l.mdxType="string"==typeof e?e:a,c[1]=l;for(var p=2;p<o;p++)c[p]=t[p];return r.createElement.apply(null,c)}return r.createElement.apply(null,t)}m.displayName="MDXCreateElement"},4713:function(e,n,t){t.r(n),t.d(n,{frontMatter:function(){return l},contentTitle:function(){return i},metadata:function(){return p},toc:function(){return u},default:function(){return m}});var r=t(7462),a=t(3366),o=(t(7294),t(3905)),c=["components"],l={},i="codeplea/genann",p={unversionedId:"examples/codeplea_genann",id:"examples/codeplea_genann",title:"codeplea/genann",description:"",source:"@site/docs/examples/codeplea_genann.md",sourceDirName:"examples",slug:"/examples/codeplea_genann",permalink:"/clang-build/examples/codeplea_genann",editUrl:"https://github.com/Trick-17/clang-build/docs/examples/codeplea_genann.md",tags:[],version:"current",frontMatter:{},sidebar:"examplesSidebar",previous:{title:"lz4",permalink:"/clang-build/examples/lz4"},next:{title:"nikoreun/tinygrad",permalink:"/clang-build/examples/nikoreun_tinygrad"}},u=[],s={toc:u};function m(e){var n=e.components,t=(0,a.Z)(e,c);return(0,o.kt)("wrapper",(0,r.Z)({},s,t,{components:n,mdxType:"MDXLayout"}),(0,o.kt)("h1",{id:"codepleagenann"},"codeplea/genann"),(0,o.kt)("pre",null,(0,o.kt)("code",{parentName:"pre",className:"language-toml"},'url = "git@github.com:codeplea/genann.git"\nname = "genann"\n\n[genann]\n    target_type = "static library"\n    sources = ["genann.c.c"]\n\n[example1]\n    sources = ["example1.c"]\n    dependencies = ["genann"]\n\n[example2]\n    sources = ["example2.c"]\n    dependencies = ["genann"]\n\n[example3]\n    sources = ["example3.c"]\n    dependencies = ["genann"]\n\n[example4]\n    sources = ["example4.c"]\n    dependencies = ["genann"]\n\n[test]\n    sources = ["test.c"]\n    dependencies = ["genann"]\n')))}m.isMDXComponent=!0}}]);