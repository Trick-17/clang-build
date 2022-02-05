"use strict";(self.webpackChunkmy_website=self.webpackChunkmy_website||[]).push([[5977],{3905:function(e,t,n){n.d(t,{Zo:function(){return s},kt:function(){return f}});var r=n(7294);function a(e,t,n){return t in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}function l(e,t){var n=Object.keys(e);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(e);t&&(r=r.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),n.push.apply(n,r)}return n}function i(e){for(var t=1;t<arguments.length;t++){var n=null!=arguments[t]?arguments[t]:{};t%2?l(Object(n),!0).forEach((function(t){a(e,t,n[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(n)):l(Object(n)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(n,t))}))}return e}function p(e,t){if(null==e)return{};var n,r,a=function(e,t){if(null==e)return{};var n,r,a={},l=Object.keys(e);for(r=0;r<l.length;r++)n=l[r],t.indexOf(n)>=0||(a[n]=e[n]);return a}(e,t);if(Object.getOwnPropertySymbols){var l=Object.getOwnPropertySymbols(e);for(r=0;r<l.length;r++)n=l[r],t.indexOf(n)>=0||Object.prototype.propertyIsEnumerable.call(e,n)&&(a[n]=e[n])}return a}var o=r.createContext({}),u=function(e){var t=r.useContext(o),n=t;return e&&(n="function"==typeof e?e(t):i(i({},t),e)),n},s=function(e){var t=u(e.components);return r.createElement(o.Provider,{value:t},e.children)},c={inlineCode:"code",wrapper:function(e){var t=e.children;return r.createElement(r.Fragment,{},t)}},d=r.forwardRef((function(e,t){var n=e.components,a=e.mdxType,l=e.originalType,o=e.parentName,s=p(e,["components","mdxType","originalType","parentName"]),d=u(n),f=a,m=d["".concat(o,".").concat(f)]||d[f]||c[f]||l;return n?r.createElement(m,i(i({ref:t},s),{},{components:n})):r.createElement(m,i({ref:t},s))}));function f(e,t){var n=arguments,a=t&&t.mdxType;if("string"==typeof e||a){var l=n.length,i=new Array(l);i[0]=d;var p={};for(var o in t)hasOwnProperty.call(t,o)&&(p[o]=t[o]);p.originalType=e,p.mdxType="string"==typeof e?e:a,i[1]=p;for(var u=2;u<l;u++)i[u]=n[u];return r.createElement.apply(null,i)}return r.createElement.apply(null,n)}d.displayName="MDXCreateElement"},8678:function(e,t,n){n.r(t),n.d(t,{frontMatter:function(){return p},contentTitle:function(){return o},metadata:function(){return u},toc:function(){return s},default:function(){return d}});var r=n(7462),a=n(3366),l=(n(7294),n(3905)),i=["components"],p={},o="Target settings",u={unversionedId:"config_reference/target",id:"config_reference/target",title:"Target settings",description:"Declaration",source:"@site/docs/config_reference/target.md",sourceDirName:"config_reference",slug:"/config_reference/target",permalink:"/clang-build/config_reference/target",editUrl:"https://github.com/Trick-17/clang-build/docs/config_reference/target.md",tags:[],version:"current",frontMatter:{},sidebar:"configSidebar",next:{title:"Project settings",permalink:"/clang-build/config_reference/project"}},s=[{value:"Declaration",id:"declaration",children:[],level:2},{value:"General parameters",id:"general-parameters",children:[],level:2},{value:"Source parameters",id:"source-parameters",children:[],level:2},{value:"Flag parameters",id:"flag-parameters",children:[],level:2},{value:"Output parameters",id:"output-parameters",children:[],level:2}],c={toc:s};function d(e){var t=e.components,n=(0,a.Z)(e,i);return(0,l.kt)("wrapper",(0,r.Z)({},c,n,{components:t,mdxType:"MDXLayout"}),(0,l.kt)("h1",{id:"target-settings"},"Target settings"),(0,l.kt)("h2",{id:"declaration"},"Declaration"),(0,l.kt)("p",null,'A target can be declared with a name square brackets.\nIf none are specified, the default name is "main".'),(0,l.kt)("h2",{id:"general-parameters"},"General parameters"),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"url")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        string\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),':     ""'),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"version")," (optional)"),(0,l.kt)("p",null,"This only has an effect if a url was specified."),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        string\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),':     ""'),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"directory")," (optional)"),(0,l.kt)("p",null,"Note, if a url is specified, this is relative to the source root."),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        string\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),':     ""'),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"target_type")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        string\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),':     if sources are found "executable", else "header only"\n:',(0,l.kt)("inlineCode",{parentName:"p"},"options"),':     "executable", "shared library", "static library", "header only"'),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"dependencies")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        list of strings\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),":     []"),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"public_dependencies")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        list of strings\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),":     []"),(0,l.kt)("h2",{id:"source-parameters"},"Source parameters"),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"include_directories")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        list of strings\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),":     []"),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"public_include_directories")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        list of strings\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),":     []"),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"sources")," (optional)"),(0,l.kt)("p",null,"You can list files and/or glob patterns."),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        list of strings\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),':     if a "src" folder is present, any sources that are found inside, else any sources found in the target directory'),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"sources_exclude")," (optional)"),(0,l.kt)("p",null,"You can list files and/or glob patterns."),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        list of strings\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),":     []"),(0,l.kt)("h2",{id:"flag-parameters"},"Flag parameters"),(0,l.kt)("p",null,"Flags can be specified inside one of the following secions"),(0,l.kt)("ul",null,(0,l.kt)("li",{parentName:"ul"},"flags"),(0,l.kt)("li",{parentName:"ul"},"public_flags"),(0,l.kt)("li",{parentName:"ul"},"interface_flags")),(0,l.kt)("p",null,"or nested into a platform-spcific section"),(0,l.kt)("ul",null,(0,l.kt)("li",{parentName:"ul"},"linux"),(0,l.kt)("li",{parentName:"ul"},"osx"),(0,l.kt)("li",{parentName:"ul"},"windows")),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"compile")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        list of strings\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),":     []"),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"link")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        list of strings\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),":     []"),(0,l.kt)("h2",{id:"output-parameters"},"Output parameters"),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"output_name")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        string\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),':     ""'),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"output_prefix")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        string\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),':     ""'),(0,l.kt)("p",null,(0,l.kt)("strong",{parentName:"p"},"output_suffix")," (optional)"),(0,l.kt)("p",null,":",(0,l.kt)("inlineCode",{parentName:"p"},"type"),":        string\n:",(0,l.kt)("inlineCode",{parentName:"p"},"default"),':     ""'))}d.isMDXComponent=!0}}]);