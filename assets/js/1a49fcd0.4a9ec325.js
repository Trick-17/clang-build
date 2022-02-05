"use strict";(self.webpackChunkmy_website=self.webpackChunkmy_website||[]).push([[8563],{3905:function(e,t,n){n.d(t,{Zo:function(){return c},kt:function(){return f}});var r=n(7294);function a(e,t,n){return t in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}function i(e,t){var n=Object.keys(e);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(e);t&&(r=r.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),n.push.apply(n,r)}return n}function l(e){for(var t=1;t<arguments.length;t++){var n=null!=arguments[t]?arguments[t]:{};t%2?i(Object(n),!0).forEach((function(t){a(e,t,n[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(n)):i(Object(n)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(n,t))}))}return e}function o(e,t){if(null==e)return{};var n,r,a=function(e,t){if(null==e)return{};var n,r,a={},i=Object.keys(e);for(r=0;r<i.length;r++)n=i[r],t.indexOf(n)>=0||(a[n]=e[n]);return a}(e,t);if(Object.getOwnPropertySymbols){var i=Object.getOwnPropertySymbols(e);for(r=0;r<i.length;r++)n=i[r],t.indexOf(n)>=0||Object.prototype.propertyIsEnumerable.call(e,n)&&(a[n]=e[n])}return a}var u=r.createContext({}),d=function(e){var t=r.useContext(u),n=t;return e&&(n="function"==typeof e?e(t):l(l({},t),e)),n},c=function(e){var t=d(e.components);return r.createElement(u.Provider,{value:t},e.children)},s={inlineCode:"code",wrapper:function(e){var t=e.children;return r.createElement(r.Fragment,{},t)}},p=r.forwardRef((function(e,t){var n=e.components,a=e.mdxType,i=e.originalType,u=e.parentName,c=o(e,["components","mdxType","originalType","parentName"]),p=d(n),f=a,m=p["".concat(u,".").concat(f)]||p[f]||s[f]||i;return n?r.createElement(m,l(l({ref:t},c),{},{components:n})):r.createElement(m,l({ref:t},c))}));function f(e,t){var n=arguments,a=t&&t.mdxType;if("string"==typeof e||a){var i=n.length,l=new Array(i);l[0]=p;var o={};for(var u in t)hasOwnProperty.call(t,u)&&(o[u]=t[u]);o.originalType=e,o.mdxType="string"==typeof e?e:a,l[1]=o;for(var d=2;d<i;d++)l[d]=n[d];return r.createElement.apply(null,l)}return r.createElement.apply(null,n)}p.displayName="MDXCreateElement"},2102:function(e,t,n){n.r(t),n.d(t,{frontMatter:function(){return o},contentTitle:function(){return u},metadata:function(){return d},toc:function(){return c},default:function(){return p}});var r=n(7462),a=n(3366),i=(n(7294),n(3905)),l=["components"],o={},u="Defaults",d={unversionedId:"user_guide/defaults",id:"user_guide/defaults",title:"Defaults",description:"General",source:"@site/docs/user_guide/defaults.md",sourceDirName:"user_guide",slug:"/user_guide/defaults",permalink:"/clang-build/user_guide/defaults",editUrl:"https://github.com/Trick-17/clang-build/docs/user_guide/defaults.md",tags:[],version:"current",frontMatter:{}},c=[{value:"General",id:"general",children:[],level:2},{value:"Search Paths",id:"search-paths",children:[],level:2},{value:"Build Type and Flags",id:"build-type-and-flags",children:[],level:2},{value:"Build Directories",id:"build-directories",children:[],level:2}],s={toc:c};function p(e){var t=e.components,n=(0,a.Z)(e,l);return(0,i.kt)("wrapper",(0,r.Z)({},s,n,{components:t,mdxType:"MDXLayout"}),(0,i.kt)("h1",{id:"defaults"},"Defaults"),(0,i.kt)("h2",{id:"general"},"General"),(0,i.kt)("p",null,"By default:"),(0,i.kt)("ul",null,(0,i.kt)("li",{parentName:"ul"},"all relative paths in a toml are interpreted as relative to that toml file"),(0,i.kt)("li",{parentName:"ul"},"if only one target is built from source, it is built into ",(0,i.kt)("inlineCode",{parentName:"li"},"build/<build_type>")),(0,i.kt)("li",{parentName:"ul"},"if more than one target is built from source, they are built into ",(0,i.kt)("inlineCode",{parentName:"li"},"build/<target_name>/<build_type>")),(0,i.kt)("li",{parentName:"ul"},"an external target's sources will be copied/downloaded into ",(0,i.kt)("inlineCode",{parentName:"li"},"build/<target_name>/external_sources")),(0,i.kt)("li",{parentName:"ul"},"targets for which sources are found will be built as ",(0,i.kt)("inlineCode",{parentName:"li"},"executable")),(0,i.kt)("li",{parentName:"ul"},"targets for which no sources are found will be ",(0,i.kt)("inlineCode",{parentName:"li"},"header-only"))),(0,i.kt)("h2",{id:"search-paths"},"Search Paths"),(0,i.kt)("p",null,(0,i.kt)("strong",{parentName:"p"},"Include directories")),(0,i.kt)("p",null,"Default system directories for ",(0,i.kt)("inlineCode",{parentName:"p"},"#include"),"-searches are given by Clang."),(0,i.kt)("p",null,(0,i.kt)("inlineCode",{parentName:"p"},"clang-build"),"'s include directories will be added to the search paths and will be searched\nfor header files for a target.\nIn your project file, you can add an ",(0,i.kt)("inlineCode",{parentName:"p"},"include_directories")," array to specify a target's header directories,\nwhere by default ",(0,i.kt)("inlineCode",{parentName:"p"},"clang-build"),' will try the target\'s root directory and an "include" subdirectory.'),(0,i.kt)("p",null,(0,i.kt)("strong",{parentName:"p"},"Source directories")),(0,i.kt)("p",null,(0,i.kt)("inlineCode",{parentName:"p"},"clang-build"),"'s source directories will be searched for source files for a target.\nIn your project file, you can add a ",(0,i.kt)("inlineCode",{parentName:"p"},"sources")," array of patterns to specify a target's sources,\nwhere by default ",(0,i.kt)("inlineCode",{parentName:"p"},"clang-build"),' will try the target\'s root directory and a "src" subdirectory.'),(0,i.kt)("h2",{id:"build-type-and-flags"},"Build Type and Flags"),(0,i.kt)("p",null,'For ".cpp" files, the newest available C++ standard will be used by automatically adding e.g. ',(0,i.kt)("inlineCode",{parentName:"p"},"-std=c++17"),"."),(0,i.kt)("p",null,"The ",(0,i.kt)("inlineCode",{parentName:"p"},"default")," build type contains the flags, which are used in all build configurations,\ni.e. the minimum set of flags which ",(0,i.kt)("inlineCode",{parentName:"p"},"clang-build")," enforces."),(0,i.kt)("p",null,":",(0,i.kt)("inlineCode",{parentName:"p"},"default"),":        contains ",(0,i.kt)("inlineCode",{parentName:"p"},"-Wall -Wextra -Wpedantic -Werror"),"\n:",(0,i.kt)("inlineCode",{parentName:"p"},"release"),":        adds ",(0,i.kt)("inlineCode",{parentName:"p"},"-O3 -DNDEBUG"),"\n:",(0,i.kt)("inlineCode",{parentName:"p"},"relwithdebinfo"),": adds ",(0,i.kt)("inlineCode",{parentName:"p"},"-O3 -g3 -DNDEBUG"),"\n:",(0,i.kt)("inlineCode",{parentName:"p"},"debug"),":          adds ",(0,i.kt)("inlineCode",{parentName:"p"},"-O0 -g3 -DDEBUG"),"\n:",(0,i.kt)("inlineCode",{parentName:"p"},"coverage"),":       adds debug flags and ",(0,i.kt)("inlineCode",{parentName:"p"},"--coverage -fno-inline")),(0,i.kt)("p",null,"By activating all warnings and turning them into errors, the default flags ensure that unrecommended\ncode needs to be explicitly allowed by the author."),(0,i.kt)("h2",{id:"build-directories"},"Build Directories"),(0,i.kt)("pre",null,(0,i.kt)("code",{parentName:"pre"},"build\n\u251c\u2500\u2500 myproject\n|   \u251c\u2500\u2500 targetname\n|   |   \u251c\u2500\u2500 external_sources\n|   |   \u251c\u2500\u2500 release\n|   |   |   \u251c\u2500\u2500 obj\n|   |   |   \u251c\u2500\u2500 dep\n|   |   |   \u251c\u2500\u2500 bin\n|   |   |   \u251c\u2500\u2500 lib\n|   |   |   \u2514\u2500\u2500 include\n|   |   \u251c\u2500\u2500 debug\n|   |   | \u2514\u2500\u2500 ...\n|   |   \u251c\u2500\u2500 default\n|   |   | \u2514\u2500\u2500 ...\n|   |   \u2514\u2500\u2500 ...\n|   \u2514\u2500\u2500 othertargetname\n|       \u2514\u2500\u2500 ...\n\u2514\u2500\u2500 mysubproject\n    \u2514\u2500\u2500 ...\n")),(0,i.kt)("p",null,(0,i.kt)("em",{parentName:"p"},"Note:")),(0,i.kt)("p",null,'If there is only one project, the target build folders will be placed directly into "build".\nAnalogously, if there is only one target, the "release", "debug", etc. directories will be\nplaced directly into "build".'))}p.isMDXComponent=!0}}]);