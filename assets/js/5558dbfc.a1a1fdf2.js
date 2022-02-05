"use strict";(self.webpackChunkmy_website=self.webpackChunkmy_website||[]).push([[313],{3905:function(e,t,n){n.d(t,{Zo:function(){return u},kt:function(){return m}});var o=n(7294);function r(e,t,n){return t in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}function s(e,t){var n=Object.keys(e);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);t&&(o=o.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),n.push.apply(n,o)}return n}function i(e){for(var t=1;t<arguments.length;t++){var n=null!=arguments[t]?arguments[t]:{};t%2?s(Object(n),!0).forEach((function(t){r(e,t,n[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(n)):s(Object(n)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(n,t))}))}return e}function a(e,t){if(null==e)return{};var n,o,r=function(e,t){if(null==e)return{};var n,o,r={},s=Object.keys(e);for(o=0;o<s.length;o++)n=s[o],t.indexOf(n)>=0||(r[n]=e[n]);return r}(e,t);if(Object.getOwnPropertySymbols){var s=Object.getOwnPropertySymbols(e);for(o=0;o<s.length;o++)n=s[o],t.indexOf(n)>=0||Object.prototype.propertyIsEnumerable.call(e,n)&&(r[n]=e[n])}return r}var c=o.createContext({}),l=function(e){var t=o.useContext(c),n=t;return e&&(n="function"==typeof e?e(t):i(i({},t),e)),n},u=function(e){var t=l(e.components);return o.createElement(c.Provider,{value:t},e.children)},p={inlineCode:"code",wrapper:function(e){var t=e.children;return o.createElement(o.Fragment,{},t)}},b=o.forwardRef((function(e,t){var n=e.components,r=e.mdxType,s=e.originalType,c=e.parentName,u=a(e,["components","mdxType","originalType","parentName"]),b=l(n),m=r,f=b["".concat(c,".").concat(m)]||b[m]||p[m]||s;return n?o.createElement(f,i(i({ref:t},u),{},{components:n})):o.createElement(f,i({ref:t},u))}));function m(e,t){var n=arguments,r=t&&t.mdxType;if("string"==typeof e||r){var s=n.length,i=new Array(s);i[0]=b;var a={};for(var c in t)hasOwnProperty.call(t,c)&&(a[c]=t[c]);a.originalType=e,a.mdxType="string"==typeof e?e:r,i[1]=a;for(var l=2;l<s;l++)i[l]=n[l];return o.createElement.apply(null,i)}return o.createElement.apply(null,n)}b.displayName="MDXCreateElement"},9263:function(e,t,n){n.r(t),n.d(t,{frontMatter:function(){return a},contentTitle:function(){return c},metadata:function(){return l},toc:function(){return u},default:function(){return b}});var o=n(7462),r=n(3366),s=(n(7294),n(3905)),i=["components"],a={},c="boost/filesystem",l={unversionedId:"examples/boost_filesystem",id:"examples/boost_filesystem",title:"boost/filesystem",description:"This example contains what you need in order to build boost/filesystem, but",source:"@site/docs/examples/boost_filesystem.md",sourceDirName:"examples",slug:"/examples/boost_filesystem",permalink:"/clang-build/examples/boost_filesystem",editUrl:"https://github.com/Trick-17/clang-build/docs/examples/boost_filesystem.md",tags:[],version:"current",frontMatter:{},sidebar:"examplesSidebar",next:{title:"GLFW",permalink:"/clang-build/examples/glfw"}},u=[],p={toc:u};function b(e){var t=e.components,n=(0,r.Z)(e,i);return(0,s.kt)("wrapper",(0,o.Z)({},p,n,{components:t,mdxType:"MDXLayout"}),(0,s.kt)("h1",{id:"boostfilesystem"},"boost/filesystem"),(0,s.kt)("p",null,"This example contains what you need in order to build boost/filesystem, but\nfor now without examples or tests. It requires a few other boost-libraries,\nmost of which are header-only."),(0,s.kt)("pre",null,(0,s.kt)("code",{parentName:"pre",className:"language-toml"},'name = "boost"\n\n[filesystem]\n    target_type = "static library"\n    url = "https://github.com/boostorg/filesystem"\n    version = "boost-1.65.0"\n    dependencies = ["detail"]\n    public_dependencies = ["assert", "config", "core", "io", "iterator", "functional", "mpl", "predef", "range", "smart_ptr", "static_assert", "system", "throw_exception", "type_traits"]\n    [filesystem.flags]\n        compile = ["-Wno-parentheses-equality", "-Wno-unused-parameter", "-Wno-nested-anon-types", "-Wno-vla-extension", "-Wno-pedantic"]\n\n[system]\n    target_type = "static library"\n    url = "https://github.com/boostorg/system"\n    version = "boost-1.65.0"\n    dependencies = ["core", "winapi", "config", "predef", "assert"]\n    [system.public_flags]\n        compile = [\'-DBOOST_NO_CXX11_HDR_SYSTEM_ERROR\', \'-Wno-deprecated-declarations\', \'-Wno-language-extension-token\']\n\n[winapi]\n    url = "https://github.com/boostorg/winapi"\n    version = "boost-1.65.0"\n\n[config]\n    url = "https://github.com/boostorg/config"\n    version = "boost-1.65.0"\n\n[core]\n    url = "https://github.com/boostorg/core"\n    version = "boost-1.65.0"\n\n[smart_ptr]\n    url = "https://github.com/boostorg/smart_ptr"\n    version = "boost-1.65.0"\n\n[preprocessor]\n    url = "https://github.com/boostorg/preprocessor"\n    version = "boost-1.65.0"\n\n[mpl]\n    url = "https://github.com/boostorg/mpl"\n    version = "boost-1.65.0"\n    dependencies = ["preprocessor"]\n\n[io]\n    url = "https://github.com/boostorg/io"\n    version = "boost-1.65.0"\n\n[detail]\n    url = "https://github.com/boostorg/detail"\n    version = "boost-1.65.0"\n\n[functional]\n    url = "https://github.com/boostorg/functional"\n    version = "boost-1.65.0"\n\n[throw_exception]\n    url = "https://github.com/boostorg/throw_exception"\n    version = "boost-1.65.0"\n\n[iterator]\n    url = "https://github.com/boostorg/iterator"\n    version = "boost-1.65.0"\n    dependencies = ["detail"]\n\n[predef]\n    url = "https://github.com/boostorg/predef"\n    version = "boost-1.65.0"\n\n[range]\n    url = "https://github.com/boostorg/range"\n    version = "boost-1.65.0"\n\n[assert]\n    url = "https://github.com/boostorg/assert"\n    version = "boost-1.65.0"\n\n[static_assert] # has sources which should not be included\n    target_type = "header only"\n    url = "https://github.com/boostorg/static_assert"\n    version = "boost-1.65.0"\n\n[utility] # has sources which should not be included\n    target_type = "header only"\n    url = "https://github.com/boostorg/utility"\n    version = "boost-1.65.0"\n\n[type_traits]\n    url = "https://github.com/boostorg/type_traits"\n    version = "boost-1.65.0"\n')))}b.isMDXComponent=!0}}]);