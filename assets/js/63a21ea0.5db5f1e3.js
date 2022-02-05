"use strict";(self.webpackChunkmy_website=self.webpackChunkmy_website||[]).push([[9623],{3905:function(e,t,n){n.d(t,{Zo:function(){return s},kt:function(){return d}});var r=n(7294);function o(e,t,n){return t in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}function a(e,t){var n=Object.keys(e);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(e);t&&(r=r.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),n.push.apply(n,r)}return n}function i(e){for(var t=1;t<arguments.length;t++){var n=null!=arguments[t]?arguments[t]:{};t%2?a(Object(n),!0).forEach((function(t){o(e,t,n[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(n)):a(Object(n)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(n,t))}))}return e}function l(e,t){if(null==e)return{};var n,r,o=function(e,t){if(null==e)return{};var n,r,o={},a=Object.keys(e);for(r=0;r<a.length;r++)n=a[r],t.indexOf(n)>=0||(o[n]=e[n]);return o}(e,t);if(Object.getOwnPropertySymbols){var a=Object.getOwnPropertySymbols(e);for(r=0;r<a.length;r++)n=a[r],t.indexOf(n)>=0||Object.prototype.propertyIsEnumerable.call(e,n)&&(o[n]=e[n])}return o}var u=r.createContext({}),c=function(e){var t=r.useContext(u),n=t;return e&&(n="function"==typeof e?e(t):i(i({},t),e)),n},s=function(e){var t=c(e.components);return r.createElement(u.Provider,{value:t},e.children)},p={inlineCode:"code",wrapper:function(e){var t=e.children;return r.createElement(r.Fragment,{},t)}},m=r.forwardRef((function(e,t){var n=e.components,o=e.mdxType,a=e.originalType,u=e.parentName,s=l(e,["components","mdxType","originalType","parentName"]),m=c(n),d=o,f=m["".concat(u,".").concat(d)]||m[d]||p[d]||a;return n?r.createElement(f,i(i({ref:t},s),{},{components:n})):r.createElement(f,i({ref:t},s))}));function d(e,t){var n=arguments,o=t&&t.mdxType;if("string"==typeof e||o){var a=n.length,i=new Array(a);i[0]=m;var l={};for(var u in t)hasOwnProperty.call(t,u)&&(l[u]=t[u]);l.originalType=e,l.mdxType="string"==typeof e?e:o,i[1]=l;for(var c=2;c<a;c++)i[c]=n[c];return r.createElement.apply(null,i)}return r.createElement.apply(null,n)}m.displayName="MDXCreateElement"},968:function(e,t,n){n.r(t),n.d(t,{frontMatter:function(){return l},contentTitle:function(){return u},metadata:function(){return c},toc:function(){return s},default:function(){return m}});var r=n(7462),o=n(3366),a=(n(7294),n(3905)),i=["components"],l={},u="Customisations",c={unversionedId:"user_guide/customizations",id:"version-0.0.0/user_guide/customizations",title:"Customisations",description:"Let's have a look at some of the ways you can configure your project, if it does not have",source:"@site/versioned_docs/version-0.0.0/user_guide/customizations.md",sourceDirName:"user_guide",slug:"/user_guide/customizations",permalink:"/clang-build/0.0.0/user_guide/customizations",editUrl:"https://github.com/Trick-17/clang-build/versioned_docs/version-0.0.0/user_guide/customizations.md",tags:[],version:"0.0.0",frontMatter:{}},s=[{value:"Custom target name",id:"custom-target-name",children:[],level:2},{value:"Custom folder names",id:"custom-folder-names",children:[],level:2},{value:"Compiling a library",id:"compiling-a-library",children:[],level:2}],p={toc:s};function m(e){var t=e.components,n=(0,o.Z)(e,i);return(0,a.kt)("wrapper",(0,r.Z)({},p,n,{components:t,mdxType:"MDXLayout"}),(0,a.kt)("h1",{id:"customisations"},"Customisations"),(0,a.kt)("p",null,"Let's have a look at some of the ways you can configure your project, if it does not have\na default setup such as in the example above."),(0,a.kt)("h2",{id:"custom-target-name"},"Custom target name"),(0,a.kt)("p",null,"First you might want to customize the name of the executable of your project. To do this you can\nadd a ",(0,a.kt)("inlineCode",{parentName:"p"},"clang-build.toml")," file to your project."),(0,a.kt)("pre",null,(0,a.kt)("code",{parentName:"pre"},"my_project\n\u251c\u2500\u2500 include\n|   \u251c\u2500\u2500 cool_features.hpp\n|   \u2514\u2500\u2500 math_lib.hpp\n\u251c\u2500\u2500 src\n|   \u251c\u2500\u2500 cool_features.cpp\n|   \u2514\u2500\u2500 my_app.cpp\n\u2514\u2500\u2500 clang-build.toml\n")),(0,a.kt)("p",null,"The ",(0,a.kt)("inlineCode",{parentName:"p"},"toml")," file looks as follows:"),(0,a.kt)("pre",null,(0,a.kt)("code",{parentName:"pre",className:"language-toml"},'[myexe]\n    output_name = "MyNextApp-v1.0"\n')),(0,a.kt)("p",null,"Here the square brackets define a target. Since only the ",(0,a.kt)("inlineCode",{parentName:"p"},"output_name")," is given, clang-build continues\nto assume that a default project is inside this folder, with the default folder names. This is of course\nthe case in the example above sou you can simply call:"),(0,a.kt)("pre",null,(0,a.kt)("code",{parentName:"pre"},"clang-build\n")),(0,a.kt)("p",null,"and your project get's compiled."),(0,a.kt)("h2",{id:"custom-folder-names"},"Custom folder names"),(0,a.kt)("p",null,"While it is common to have a folder structure like the one above, maybe for some reason\nthe folders are called differently in your project. While automatic detection now does not\nwork, you can just specify the folder names in your ",(0,a.kt)("inlineCode",{parentName:"p"},"toml"),"-file."),(0,a.kt)("pre",null,(0,a.kt)("code",{parentName:"pre"},"my_project\n\u251c\u2500\u2500 header_files\n|   \u251c\u2500\u2500 cool_features.hpp\n|   \u2514\u2500\u2500 math_lib.hpp\n\u251c\u2500\u2500 external_header_files\n|   \u251c\u2500\u2500 collaborator1_interface.hpp\n|   \u2514\u2500\u2500 collaborator2_interface.hpp\n\u251c\u2500\u2500 sauce\n|   \u251c\u2500\u2500 cool_features.cpp\n|   \u2514\u2500\u2500 my_app.cpp\n\u2514\u2500\u2500 clang-build.toml\n")),(0,a.kt)("p",null,"The ",(0,a.kt)("inlineCode",{parentName:"p"},"toml")," file now looks as follows:"),(0,a.kt)("pre",null,(0,a.kt)("code",{parentName:"pre",className:"language-toml"},'[myexe]\n    output_name = "MyNextApp-v1.0"\n    include_directories = ["header_files", "external_header_files"]\n    sources = ["sauce/*.cpp"]\n')),(0,a.kt)("h2",{id:"compiling-a-library"},"Compiling a library"),(0,a.kt)("p",null,"If you want to compile a library instead of an executable, you can simply change\nthe target type in the toml file:"),(0,a.kt)("pre",null,(0,a.kt)("code",{parentName:"pre",className:"language-toml"},'[mylib]\n    output_name = "MyNextLibrary-v1.0"\n    target_type = "shared library"\n\n[mylib-static]\n    output_name = "MyNextLibrary-static-v1.0"\n    target_type = "static library"\n')))}m.isMDXComponent=!0}}]);