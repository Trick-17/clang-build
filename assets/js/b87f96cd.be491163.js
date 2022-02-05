"use strict";(self.webpackChunkmy_website=self.webpackChunkmy_website||[]).push([[5074],{3905:function(e,n,r){r.d(n,{Zo:function(){return p},kt:function(){return m}});var t=r(7294);function o(e,n,r){return n in e?Object.defineProperty(e,n,{value:r,enumerable:!0,configurable:!0,writable:!0}):e[n]=r,e}function i(e,n){var r=Object.keys(e);if(Object.getOwnPropertySymbols){var t=Object.getOwnPropertySymbols(e);n&&(t=t.filter((function(n){return Object.getOwnPropertyDescriptor(e,n).enumerable}))),r.push.apply(r,t)}return r}function a(e){for(var n=1;n<arguments.length;n++){var r=null!=arguments[n]?arguments[n]:{};n%2?i(Object(r),!0).forEach((function(n){o(e,n,r[n])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(r)):i(Object(r)).forEach((function(n){Object.defineProperty(e,n,Object.getOwnPropertyDescriptor(r,n))}))}return e}function c(e,n){if(null==e)return{};var r,t,o=function(e,n){if(null==e)return{};var r,t,o={},i=Object.keys(e);for(t=0;t<i.length;t++)r=i[t],n.indexOf(r)>=0||(o[r]=e[r]);return o}(e,n);if(Object.getOwnPropertySymbols){var i=Object.getOwnPropertySymbols(e);for(t=0;t<i.length;t++)r=i[t],n.indexOf(r)>=0||Object.prototype.propertyIsEnumerable.call(e,r)&&(o[r]=e[r])}return o}var u=t.createContext({}),l=function(e){var n=t.useContext(u),r=n;return e&&(r="function"==typeof e?e(n):a(a({},n),e)),r},p=function(e){var n=l(e.components);return t.createElement(u.Provider,{value:n},e.children)},s={inlineCode:"code",wrapper:function(e){var n=e.children;return t.createElement(t.Fragment,{},n)}},d=t.forwardRef((function(e,n){var r=e.components,o=e.mdxType,i=e.originalType,u=e.parentName,p=c(e,["components","mdxType","originalType","parentName"]),d=l(r),m=o,g=d["".concat(u,".").concat(m)]||d[m]||s[m]||i;return r?t.createElement(g,a(a({ref:n},p),{},{components:r})):t.createElement(g,a({ref:n},p))}));function m(e,n){var r=arguments,o=n&&n.mdxType;if("string"==typeof e||o){var i=r.length,a=new Array(i);a[0]=d;var c={};for(var u in n)hasOwnProperty.call(n,u)&&(c[u]=n[u]);c.originalType=e,c.mdxType="string"==typeof e?e:o,a[1]=c;for(var l=2;l<i;l++)a[l]=r[l];return t.createElement.apply(null,a)}return t.createElement.apply(null,r)}d.displayName="MDXCreateElement"},3610:function(e,n,r){r.r(n),r.d(n,{frontMatter:function(){return c},contentTitle:function(){return u},metadata:function(){return l},toc:function(){return p},default:function(){return d}});var t=r(7462),o=r(3366),i=(r(7294),r(3905)),a=["components"],c={},u="nikoreun/tinygrad",l={unversionedId:"examples/nikoreun_tinygrad",id:"version-0.0.0/examples/nikoreun_tinygrad",title:"nikoreun/tinygrad",description:"",source:"@site/versioned_docs/version-0.0.0/examples/nikoreun_tinygrad.md",sourceDirName:"examples",slug:"/examples/nikoreun_tinygrad",permalink:"/clang-build/0.0.0/examples/nikoreun_tinygrad",editUrl:"https://github.com/Trick-17/clang-build/versioned_docs/version-0.0.0/examples/nikoreun_tinygrad.md",tags:[],version:"0.0.0",frontMatter:{}},p=[],s={toc:p};function d(e){var n=e.components,r=(0,o.Z)(e,a);return(0,i.kt)("wrapper",(0,t.Z)({},s,r,{components:n,mdxType:"MDXLayout"}),(0,i.kt)("h1",{id:"nikoreuntinygrad"},"nikoreun/tinygrad"),(0,i.kt)("pre",null,(0,i.kt)("code",{parentName:"pre",className:"language-toml"},'name = "tinygrad"\nurl = "git@github.com:nikoreun/tinygrad.git"\n\n[tinygrad]\n    target_type = "static library"\n    public_dependencies = ["Eigen"]\n\n[example-autoencoder]\n    sources = ["examples/test_autoencoder.cpp"]\n    dependencies = ["tinygrad"]\n\n[example-logistic-regression]\n    sources = ["examples/test_logistic_regression.cpp"]\n    dependencies = ["tinygrad"]\n\n[example-neural-network]\n    sources = ["examples/test_neural_network.cpp"]\n    dependencies = ["tinygrad"]\n\n[Eigen]\n    url = "https://gitlab.com/libeigen/eigen.git"\n    target_type = "header only"\n    [Eigen.flags]\n        compile = ["-DEIGEN_HAS_STD_RESULT_OF=0", "-Wno-deprecated-declarations", "-Wno-shadow"]\n        compile_release = ["-DEIGEN_NO_DEBUG"]\n')))}d.isMDXComponent=!0}}]);