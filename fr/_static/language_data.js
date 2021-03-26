/*
 * language_data.js
 * ~~~~~~~~~~~~~~~~
 *
 * This script contains the language-specific data used by searchtools.js,
 * namely the list of stopwords, stemmer, scorer and splitter.
 *
 * :copyright: Copyright 2007-2021 by the Sphinx team, see AUTHORS.
 * :license: BSD, see LICENSE for details.
 *
 */

var stopwords = ["ai","aie","aient","aies","ait","as","au","aura","aurai","auraient","aurais","aurait","auras","aurez","auriez","aurions","aurons","auront","aux","avaient","avais","avait","avec","avez","aviez","avions","avons","ayant","ayez","ayons","c","ce","ceci","cela","cel\u00e0","ces","cet","cette","d","dans","de","des","du","elle","en","es","est","et","eu","eue","eues","eurent","eus","eusse","eussent","eusses","eussiez","eussions","eut","eux","e\u00fbmes","e\u00fbt","e\u00fbtes","furent","fus","fusse","fussent","fusses","fussiez","fussions","fut","f\u00fbmes","f\u00fbt","f\u00fbtes","ici","il","ils","j","je","l","la","le","les","leur","leurs","lui","m","ma","mais","me","mes","moi","mon","m\u00eame","n","ne","nos","notre","nous","on","ont","ou","par","pas","pour","qu","que","quel","quelle","quelles","quels","qui","s","sa","sans","se","sera","serai","seraient","serais","serait","seras","serez","seriez","serions","serons","seront","ses","soi","soient","sois","soit","sommes","son","sont","soyez","soyons","suis","sur","t","ta","te","tes","toi","ton","tu","un","une","vos","votre","vous","y","\u00e0","\u00e9taient","\u00e9tais","\u00e9tait","\u00e9tant","\u00e9tiez","\u00e9tions","\u00e9t\u00e9","\u00e9t\u00e9e","\u00e9t\u00e9es","\u00e9t\u00e9s","\u00eates"];


/* Non-minified version is copied as a separate JS file, is available */
BaseStemmer=function(){this.setCurrent=function(r){this.current=r;this.cursor=0;this.limit=this.current.length;this.limit_backward=0;this.bra=this.cursor;this.ket=this.limit};this.getCurrent=function(){return this.current};this.copy_from=function(r){this.current=r.current;this.cursor=r.cursor;this.limit=r.limit;this.limit_backward=r.limit_backward;this.bra=r.bra;this.ket=r.ket};this.in_grouping=function(r,t,i){if(this.cursor>=this.limit)return false;var s=this.current.charCodeAt(this.cursor);if(s>i||s<t)return false;s-=t;if((r[s>>>3]&1<<(s&7))==0)return false;this.cursor++;return true};this.in_grouping_b=function(r,t,i){if(this.cursor<=this.limit_backward)return false;var s=this.current.charCodeAt(this.cursor-1);if(s>i||s<t)return false;s-=t;if((r[s>>>3]&1<<(s&7))==0)return false;this.cursor--;return true};this.out_grouping=function(r,t,i){if(this.cursor>=this.limit)return false;var s=this.current.charCodeAt(this.cursor);if(s>i||s<t){this.cursor++;return true}s-=t;if((r[s>>>3]&1<<(s&7))==0){this.cursor++;return true}return false};this.out_grouping_b=function(r,t,i){if(this.cursor<=this.limit_backward)return false;var s=this.current.charCodeAt(this.cursor-1);if(s>i||s<t){this.cursor--;return true}s-=t;if((r[s>>>3]&1<<(s&7))==0){this.cursor--;return true}return false};this.eq_s=function(r){if(this.limit-this.cursor<r.length)return false;if(this.current.slice(this.cursor,this.cursor+r.length)!=r){return false}this.cursor+=r.length;return true};this.eq_s_b=function(r){if(this.cursor-this.limit_backward<r.length)return false;if(this.current.slice(this.cursor-r.length,this.cursor)!=r){return false}this.cursor-=r.length;return true};this.find_among=function(r){var t=0;var i=r.length;var s=this.cursor;var e=this.limit;var h=0;var u=0;var n=false;while(true){var c=t+(i-t>>>1);var a=0;var f=h<u?h:u;var l=r[c];var o;for(o=f;o<l[0].length;o++){if(s+f==e){a=-1;break}a=this.current.charCodeAt(s+f)-l[0].charCodeAt(o);if(a!=0)break;f++}if(a<0){i=c;u=f}else{t=c;h=f}if(i-t<=1){if(t>0)break;if(i==t)break;if(n)break;n=true}}do{var l=r[t];if(h>=l[0].length){this.cursor=s+l[0].length;if(l.length<4)return l[2];var v=l[3](this);this.cursor=s+l[0].length;if(v)return l[2]}t=l[1]}while(t>=0);return 0};this.find_among_b=function(r){var t=0;var i=r.length;var s=this.cursor;var e=this.limit_backward;var h=0;var u=0;var n=false;while(true){var c=t+(i-t>>1);var a=0;var f=h<u?h:u;var l=r[c];var o;for(o=l[0].length-1-f;o>=0;o--){if(s-f==e){a=-1;break}a=this.current.charCodeAt(s-1-f)-l[0].charCodeAt(o);if(a!=0)break;f++}if(a<0){i=c;u=f}else{t=c;h=f}if(i-t<=1){if(t>0)break;if(i==t)break;if(n)break;n=true}}do{var l=r[t];if(h>=l[0].length){this.cursor=s-l[0].length;if(l.length<4)return l[2];var v=l[3](this);this.cursor=s-l[0].length;if(v)return l[2]}t=l[1]}while(t>=0);return 0};this.replace_s=function(r,t,i){var s=i.length-(t-r);this.current=this.current.slice(0,r)+i+this.current.slice(t);this.limit+=s;if(this.cursor>=t)this.cursor+=s;else if(this.cursor>r)this.cursor=r;return s};this.slice_check=function(){if(this.bra<0||this.bra>this.ket||this.ket>this.limit||this.limit>this.current.length){return false}return true};this.slice_from=function(r){var t=false;if(this.slice_check()){this.replace_s(this.bra,this.ket,r);t=true}return t};this.slice_del=function(){return this.slice_from("")};this.insert=function(r,t,i){var s=this.replace_s(r,t,i);if(r<=this.bra)this.bra+=s;if(r<=this.ket)this.ket+=s};this.slice_to=function(){var r="";if(this.slice_check()){r=this.current.slice(this.bra,this.ket)}return r};this.assign_to=function(){return this.current.slice(0,this.limit)}};
FrenchStemmer=function(){var r=new BaseStemmer;var e=[["col",-1,-1],["par",-1,-1],["tap",-1,-1]];var i=[["",-1,7],["H",0,6],["He",1,4],["Hi",1,5],["I",0,1],["U",0,2],["Y",0,3]];var s=[["iqU",-1,3],["abl",-1,3],["Ièr",-1,4],["ièr",-1,4],["eus",-1,2],["iv",-1,1]];var a=[["ic",-1,2],["abil",-1,1],["iv",-1,3]];var u=[["iqUe",-1,1],["atrice",-1,2],["ance",-1,1],["ence",-1,5],["logie",-1,3],["able",-1,1],["isme",-1,1],["euse",-1,11],["iste",-1,1],["ive",-1,8],["if",-1,8],["usion",-1,4],["ation",-1,2],["ution",-1,4],["ateur",-1,2],["iqUes",-1,1],["atrices",-1,2],["ances",-1,1],["ences",-1,5],["logies",-1,3],["ables",-1,1],["ismes",-1,1],["euses",-1,11],["istes",-1,1],["ives",-1,8],["ifs",-1,8],["usions",-1,4],["ations",-1,2],["utions",-1,4],["ateurs",-1,2],["ments",-1,15],["ements",30,6],["issements",31,12],["ités",-1,7],["ment",-1,15],["ement",34,6],["issement",35,12],["amment",34,13],["emment",34,14],["aux",-1,10],["eaux",39,9],["eux",-1,1],["ité",-1,7]];var t=[["ira",-1,1],["ie",-1,1],["isse",-1,1],["issante",-1,1],["i",-1,1],["irai",4,1],["ir",-1,1],["iras",-1,1],["ies",-1,1],["îmes",-1,1],["isses",-1,1],["issantes",-1,1],["îtes",-1,1],["is",-1,1],["irais",13,1],["issais",13,1],["irions",-1,1],["issions",-1,1],["irons",-1,1],["issons",-1,1],["issants",-1,1],["it",-1,1],["irait",21,1],["issait",21,1],["issant",-1,1],["iraIent",-1,1],["issaIent",-1,1],["irent",-1,1],["issent",-1,1],["iront",-1,1],["ît",-1,1],["iriez",-1,1],["issiez",-1,1],["irez",-1,1],["issez",-1,1]];var c=[["a",-1,3],["era",0,2],["asse",-1,3],["ante",-1,3],["ée",-1,2],["ai",-1,3],["erai",5,2],["er",-1,2],["as",-1,3],["eras",8,2],["âmes",-1,3],["asses",-1,3],["antes",-1,3],["âtes",-1,3],["ées",-1,2],["ais",-1,3],["erais",15,2],["ions",-1,1],["erions",17,2],["assions",17,3],["erons",-1,2],["ants",-1,3],["és",-1,2],["ait",-1,3],["erait",23,2],["ant",-1,3],["aIent",-1,3],["eraIent",26,2],["èrent",-1,2],["assent",-1,3],["eront",-1,2],["ât",-1,3],["ez",-1,2],["iez",32,2],["eriez",33,2],["assiez",33,3],["erez",32,2],["é",-1,2]];var f=[["e",-1,3],["Ière",0,2],["ière",0,2],["ion",-1,1],["Ier",-1,2],["ier",-1,2]];var l=[["ell",-1,-1],["eill",-1,-1],["enn",-1,-1],["onn",-1,-1],["ett",-1,-1]];var o=[17,65,16,1,0,0,0,0,0,0,0,0,0,0,0,128,130,103,8,5];var n=[1,65,20,0,0,0,0,0,0,0,0,0,0,0,0,0,128];var b=0;var k=0;var m=0;function _(){while(true){var e=r.cursor;r:{e:while(true){var i=r.cursor;i:{s:{var s=r.cursor;a:{if(!r.in_grouping(o,97,251)){break a}r.bra=r.cursor;u:{var a=r.cursor;t:{if(!r.eq_s("u")){break t}r.ket=r.cursor;if(!r.in_grouping(o,97,251)){break t}if(!r.slice_from("U")){return false}break u}r.cursor=a;t:{if(!r.eq_s("i")){break t}r.ket=r.cursor;if(!r.in_grouping(o,97,251)){break t}if(!r.slice_from("I")){return false}break u}r.cursor=a;if(!r.eq_s("y")){break a}r.ket=r.cursor;if(!r.slice_from("Y")){return false}}break s}r.cursor=s;a:{r.bra=r.cursor;if(!r.eq_s("ë")){break a}r.ket=r.cursor;if(!r.slice_from("He")){return false}break s}r.cursor=s;a:{r.bra=r.cursor;if(!r.eq_s("ï")){break a}r.ket=r.cursor;if(!r.slice_from("Hi")){return false}break s}r.cursor=s;a:{r.bra=r.cursor;if(!r.eq_s("y")){break a}r.ket=r.cursor;if(!r.in_grouping(o,97,251)){break a}if(!r.slice_from("Y")){return false}break s}r.cursor=s;if(!r.eq_s("q")){break i}r.bra=r.cursor;if(!r.eq_s("u")){break i}r.ket=r.cursor;if(!r.slice_from("U")){return false}}r.cursor=i;break e}r.cursor=i;if(r.cursor>=r.limit){break r}r.cursor++}continue}r.cursor=e;break}return true}function v(){m=r.limit;k=r.limit;b=r.limit;var i=r.cursor;r:{e:{var s=r.cursor;i:{if(!r.in_grouping(o,97,251)){break i}if(!r.in_grouping(o,97,251)){break i}if(r.cursor>=r.limit){break i}r.cursor++;break e}r.cursor=s;i:{if(r.find_among(e)==0){break i}break e}r.cursor=s;if(r.cursor>=r.limit){break r}r.cursor++;i:while(true){s:{if(!r.in_grouping(o,97,251)){break s}break i}if(r.cursor>=r.limit){break r}r.cursor++}}m=r.cursor}r.cursor=i;var a=r.cursor;r:{e:while(true){i:{if(!r.in_grouping(o,97,251)){break i}break e}if(r.cursor>=r.limit){break r}r.cursor++}e:while(true){i:{if(!r.out_grouping(o,97,251)){break i}break e}if(r.cursor>=r.limit){break r}r.cursor++}k=r.cursor;e:while(true){i:{if(!r.in_grouping(o,97,251)){break i}break e}if(r.cursor>=r.limit){break r}r.cursor++}e:while(true){i:{if(!r.out_grouping(o,97,251)){break i}break e}if(r.cursor>=r.limit){break r}r.cursor++}b=r.cursor}r.cursor=a;return true}function d(){var e;while(true){var s=r.cursor;r:{r.bra=r.cursor;e=r.find_among(i);if(e==0){break r}r.ket=r.cursor;switch(e){case 1:if(!r.slice_from("i")){return false}break;case 2:if(!r.slice_from("u")){return false}break;case 3:if(!r.slice_from("y")){return false}break;case 4:if(!r.slice_from("ë")){return false}break;case 5:if(!r.slice_from("ï")){return false}break;case 6:if(!r.slice_del()){return false}break;case 7:if(r.cursor>=r.limit){break r}r.cursor++;break}continue}r.cursor=s;break}return true}function g(){if(!(m<=r.cursor)){return false}return true}function w(){if(!(k<=r.cursor)){return false}return true}function q(){if(!(b<=r.cursor)){return false}return true}function h(){var e;r.ket=r.cursor;e=r.find_among_b(u);if(e==0){return false}r.bra=r.cursor;switch(e){case 1:if(!q()){return false}if(!r.slice_del()){return false}break;case 2:if(!q()){return false}if(!r.slice_del()){return false}var i=r.limit-r.cursor;r:{r.ket=r.cursor;if(!r.eq_s_b("ic")){r.cursor=r.limit-i;break r}r.bra=r.cursor;e:{var t=r.limit-r.cursor;i:{if(!q()){break i}if(!r.slice_del()){return false}break e}r.cursor=r.limit-t;if(!r.slice_from("iqU")){return false}}}break;case 3:if(!q()){return false}if(!r.slice_from("log")){return false}break;case 4:if(!q()){return false}if(!r.slice_from("u")){return false}break;case 5:if(!q()){return false}if(!r.slice_from("ent")){return false}break;case 6:if(!g()){return false}if(!r.slice_del()){return false}var c=r.limit-r.cursor;r:{r.ket=r.cursor;e=r.find_among_b(s);if(e==0){r.cursor=r.limit-c;break r}r.bra=r.cursor;switch(e){case 1:if(!q()){r.cursor=r.limit-c;break r}if(!r.slice_del()){return false}r.ket=r.cursor;if(!r.eq_s_b("at")){r.cursor=r.limit-c;break r}r.bra=r.cursor;if(!q()){r.cursor=r.limit-c;break r}if(!r.slice_del()){return false}break;case 2:e:{var f=r.limit-r.cursor;i:{if(!q()){break i}if(!r.slice_del()){return false}break e}r.cursor=r.limit-f;if(!w()){r.cursor=r.limit-c;break r}if(!r.slice_from("eux")){return false}}break;case 3:if(!q()){r.cursor=r.limit-c;break r}if(!r.slice_del()){return false}break;case 4:if(!g()){r.cursor=r.limit-c;break r}if(!r.slice_from("i")){return false}break}}break;case 7:if(!q()){return false}if(!r.slice_del()){return false}var l=r.limit-r.cursor;r:{r.ket=r.cursor;e=r.find_among_b(a);if(e==0){r.cursor=r.limit-l;break r}r.bra=r.cursor;switch(e){case 1:e:{var n=r.limit-r.cursor;i:{if(!q()){break i}if(!r.slice_del()){return false}break e}r.cursor=r.limit-n;if(!r.slice_from("abl")){return false}}break;case 2:e:{var b=r.limit-r.cursor;i:{if(!q()){break i}if(!r.slice_del()){return false}break e}r.cursor=r.limit-b;if(!r.slice_from("iqU")){return false}}break;case 3:if(!q()){r.cursor=r.limit-l;break r}if(!r.slice_del()){return false}break}}break;case 8:if(!q()){return false}if(!r.slice_del()){return false}var k=r.limit-r.cursor;r:{r.ket=r.cursor;if(!r.eq_s_b("at")){r.cursor=r.limit-k;break r}r.bra=r.cursor;if(!q()){r.cursor=r.limit-k;break r}if(!r.slice_del()){return false}r.ket=r.cursor;if(!r.eq_s_b("ic")){r.cursor=r.limit-k;break r}r.bra=r.cursor;e:{var m=r.limit-r.cursor;i:{if(!q()){break i}if(!r.slice_del()){return false}break e}r.cursor=r.limit-m;if(!r.slice_from("iqU")){return false}}}break;case 9:if(!r.slice_from("eau")){return false}break;case 10:if(!w()){return false}if(!r.slice_from("al")){return false}break;case 11:r:{var _=r.limit-r.cursor;e:{if(!q()){break e}if(!r.slice_del()){return false}break r}r.cursor=r.limit-_;if(!w()){return false}if(!r.slice_from("eux")){return false}}break;case 12:if(!w()){return false}if(!r.out_grouping_b(o,97,251)){return false}if(!r.slice_del()){return false}break;case 13:if(!g()){return false}if(!r.slice_from("ant")){return false}return false;case 14:if(!g()){return false}if(!r.slice_from("ent")){return false}return false;case 15:var v=r.limit-r.cursor;if(!r.in_grouping_b(o,97,251)){return false}if(!g()){return false}r.cursor=r.limit-v;if(!r.slice_del()){return false}return false}return true}function p(){if(r.cursor<m){return false}var e=r.limit_backward;r.limit_backward=m;r.ket=r.cursor;if(r.find_among_b(t)==0){r.limit_backward=e;return false}r.bra=r.cursor;{var i=r.limit-r.cursor;r:{if(!r.eq_s_b("H")){break r}r.limit_backward=e;return false}r.cursor=r.limit-i}if(!r.out_grouping_b(o,97,251)){r.limit_backward=e;return false}if(!r.slice_del()){return false}r.limit_backward=e;return true}function z(){var e;if(r.cursor<m){return false}var i=r.limit_backward;r.limit_backward=m;r.ket=r.cursor;e=r.find_among_b(c);if(e==0){r.limit_backward=i;return false}r.bra=r.cursor;switch(e){case 1:if(!q()){r.limit_backward=i;return false}if(!r.slice_del()){return false}break;case 2:if(!r.slice_del()){return false}break;case 3:if(!r.slice_del()){return false}var s=r.limit-r.cursor;r:{r.ket=r.cursor;if(!r.eq_s_b("e")){r.cursor=r.limit-s;break r}r.bra=r.cursor;if(!r.slice_del()){return false}}break}r.limit_backward=i;return true}function I(){var e;var i=r.limit-r.cursor;r:{r.ket=r.cursor;if(!r.eq_s_b("s")){r.cursor=r.limit-i;break r}r.bra=r.cursor;var s=r.limit-r.cursor;e:{var a=r.limit-r.cursor;i:{if(!r.eq_s_b("Hi")){break i}break e}r.cursor=r.limit-a;if(!r.out_grouping_b(n,97,232)){r.cursor=r.limit-i;break r}}r.cursor=r.limit-s;if(!r.slice_del()){return false}}if(r.cursor<m){return false}var u=r.limit_backward;r.limit_backward=m;r.ket=r.cursor;e=r.find_among_b(f);if(e==0){r.limit_backward=u;return false}r.bra=r.cursor;switch(e){case 1:if(!q()){r.limit_backward=u;return false}r:{var t=r.limit-r.cursor;e:{if(!r.eq_s_b("s")){break e}break r}r.cursor=r.limit-t;if(!r.eq_s_b("t")){r.limit_backward=u;return false}}if(!r.slice_del()){return false}break;case 2:if(!r.slice_from("i")){return false}break;case 3:if(!r.slice_del()){return false}break}r.limit_backward=u;return true}function U(){var e=r.limit-r.cursor;if(r.find_among_b(l)==0){return false}r.cursor=r.limit-e;r.ket=r.cursor;if(r.cursor<=r.limit_backward){return false}r.cursor--;r.bra=r.cursor;if(!r.slice_del()){return false}return true}function H(){{var e=1;while(true){r:{if(!r.out_grouping_b(o,97,251)){break r}e--;continue}break}if(e>0){return false}}r.ket=r.cursor;r:{var i=r.limit-r.cursor;e:{if(!r.eq_s_b("é")){break e}break r}r.cursor=r.limit-i;if(!r.eq_s_b("è")){return false}}r.bra=r.cursor;if(!r.slice_from("e")){return false}return true}this.stem=function(){var e=r.cursor;_();r.cursor=e;v();r.limit_backward=r.cursor;r.cursor=r.limit;var i=r.limit-r.cursor;r:{e:{var s=r.limit-r.cursor;i:{var a=r.limit-r.cursor;s:{var u=r.limit-r.cursor;a:{if(!h()){break a}break s}r.cursor=r.limit-u;a:{if(!p()){break a}break s}r.cursor=r.limit-u;if(!z()){break i}}r.cursor=r.limit-a;var t=r.limit-r.cursor;s:{r.ket=r.cursor;a:{var c=r.limit-r.cursor;u:{if(!r.eq_s_b("Y")){break u}r.bra=r.cursor;if(!r.slice_from("i")){return false}break a}r.cursor=r.limit-c;if(!r.eq_s_b("ç")){r.cursor=r.limit-t;break s}r.bra=r.cursor;if(!r.slice_from("c")){return false}}}break e}r.cursor=r.limit-s;if(!I()){break r}}}r.cursor=r.limit-i;var f=r.limit-r.cursor;U();r.cursor=r.limit-f;var l=r.limit-r.cursor;H();r.cursor=r.limit-l;r.cursor=r.limit_backward;var o=r.cursor;d();r.cursor=o;return true};this["stemWord"]=function(e){r.setCurrent(e);this.stem();return r.getCurrent()}};
Stemmer = FrenchStemmer;



var splitChars = (function() {
    var result = {};
    var singles = [96, 180, 187, 191, 215, 247, 749, 885, 903, 907, 909, 930, 1014, 1648,
         1748, 1809, 2416, 2473, 2481, 2526, 2601, 2609, 2612, 2615, 2653, 2702,
         2706, 2729, 2737, 2740, 2857, 2865, 2868, 2910, 2928, 2948, 2961, 2971,
         2973, 3085, 3089, 3113, 3124, 3213, 3217, 3241, 3252, 3295, 3341, 3345,
         3369, 3506, 3516, 3633, 3715, 3721, 3736, 3744, 3748, 3750, 3756, 3761,
         3781, 3912, 4239, 4347, 4681, 4695, 4697, 4745, 4785, 4799, 4801, 4823,
         4881, 5760, 5901, 5997, 6313, 7405, 8024, 8026, 8028, 8030, 8117, 8125,
         8133, 8181, 8468, 8485, 8487, 8489, 8494, 8527, 11311, 11359, 11687, 11695,
         11703, 11711, 11719, 11727, 11735, 12448, 12539, 43010, 43014, 43019, 43587,
         43696, 43713, 64286, 64297, 64311, 64317, 64319, 64322, 64325, 65141];
    var i, j, start, end;
    for (i = 0; i < singles.length; i++) {
        result[singles[i]] = true;
    }
    var ranges = [[0, 47], [58, 64], [91, 94], [123, 169], [171, 177], [182, 184], [706, 709],
         [722, 735], [741, 747], [751, 879], [888, 889], [894, 901], [1154, 1161],
         [1318, 1328], [1367, 1368], [1370, 1376], [1416, 1487], [1515, 1519], [1523, 1568],
         [1611, 1631], [1642, 1645], [1750, 1764], [1767, 1773], [1789, 1790], [1792, 1807],
         [1840, 1868], [1958, 1968], [1970, 1983], [2027, 2035], [2038, 2041], [2043, 2047],
         [2070, 2073], [2075, 2083], [2085, 2087], [2089, 2307], [2362, 2364], [2366, 2383],
         [2385, 2391], [2402, 2405], [2419, 2424], [2432, 2436], [2445, 2446], [2449, 2450],
         [2483, 2485], [2490, 2492], [2494, 2509], [2511, 2523], [2530, 2533], [2546, 2547],
         [2554, 2564], [2571, 2574], [2577, 2578], [2618, 2648], [2655, 2661], [2672, 2673],
         [2677, 2692], [2746, 2748], [2750, 2767], [2769, 2783], [2786, 2789], [2800, 2820],
         [2829, 2830], [2833, 2834], [2874, 2876], [2878, 2907], [2914, 2917], [2930, 2946],
         [2955, 2957], [2966, 2968], [2976, 2978], [2981, 2983], [2987, 2989], [3002, 3023],
         [3025, 3045], [3059, 3076], [3130, 3132], [3134, 3159], [3162, 3167], [3170, 3173],
         [3184, 3191], [3199, 3204], [3258, 3260], [3262, 3293], [3298, 3301], [3312, 3332],
         [3386, 3388], [3390, 3423], [3426, 3429], [3446, 3449], [3456, 3460], [3479, 3481],
         [3518, 3519], [3527, 3584], [3636, 3647], [3655, 3663], [3674, 3712], [3717, 3718],
         [3723, 3724], [3726, 3731], [3752, 3753], [3764, 3772], [3774, 3775], [3783, 3791],
         [3802, 3803], [3806, 3839], [3841, 3871], [3892, 3903], [3949, 3975], [3980, 4095],
         [4139, 4158], [4170, 4175], [4182, 4185], [4190, 4192], [4194, 4196], [4199, 4205],
         [4209, 4212], [4226, 4237], [4250, 4255], [4294, 4303], [4349, 4351], [4686, 4687],
         [4702, 4703], [4750, 4751], [4790, 4791], [4806, 4807], [4886, 4887], [4955, 4968],
         [4989, 4991], [5008, 5023], [5109, 5120], [5741, 5742], [5787, 5791], [5867, 5869],
         [5873, 5887], [5906, 5919], [5938, 5951], [5970, 5983], [6001, 6015], [6068, 6102],
         [6104, 6107], [6109, 6111], [6122, 6127], [6138, 6159], [6170, 6175], [6264, 6271],
         [6315, 6319], [6390, 6399], [6429, 6469], [6510, 6511], [6517, 6527], [6572, 6592],
         [6600, 6607], [6619, 6655], [6679, 6687], [6741, 6783], [6794, 6799], [6810, 6822],
         [6824, 6916], [6964, 6980], [6988, 6991], [7002, 7042], [7073, 7085], [7098, 7167],
         [7204, 7231], [7242, 7244], [7294, 7400], [7410, 7423], [7616, 7679], [7958, 7959],
         [7966, 7967], [8006, 8007], [8014, 8015], [8062, 8063], [8127, 8129], [8141, 8143],
         [8148, 8149], [8156, 8159], [8173, 8177], [8189, 8303], [8306, 8307], [8314, 8318],
         [8330, 8335], [8341, 8449], [8451, 8454], [8456, 8457], [8470, 8472], [8478, 8483],
         [8506, 8507], [8512, 8516], [8522, 8525], [8586, 9311], [9372, 9449], [9472, 10101],
         [10132, 11263], [11493, 11498], [11503, 11516], [11518, 11519], [11558, 11567],
         [11622, 11630], [11632, 11647], [11671, 11679], [11743, 11822], [11824, 12292],
         [12296, 12320], [12330, 12336], [12342, 12343], [12349, 12352], [12439, 12444],
         [12544, 12548], [12590, 12592], [12687, 12689], [12694, 12703], [12728, 12783],
         [12800, 12831], [12842, 12880], [12896, 12927], [12938, 12976], [12992, 13311],
         [19894, 19967], [40908, 40959], [42125, 42191], [42238, 42239], [42509, 42511],
         [42540, 42559], [42592, 42593], [42607, 42622], [42648, 42655], [42736, 42774],
         [42784, 42785], [42889, 42890], [42893, 43002], [43043, 43055], [43062, 43071],
         [43124, 43137], [43188, 43215], [43226, 43249], [43256, 43258], [43260, 43263],
         [43302, 43311], [43335, 43359], [43389, 43395], [43443, 43470], [43482, 43519],
         [43561, 43583], [43596, 43599], [43610, 43615], [43639, 43641], [43643, 43647],
         [43698, 43700], [43703, 43704], [43710, 43711], [43715, 43738], [43742, 43967],
         [44003, 44015], [44026, 44031], [55204, 55215], [55239, 55242], [55292, 55295],
         [57344, 63743], [64046, 64047], [64110, 64111], [64218, 64255], [64263, 64274],
         [64280, 64284], [64434, 64466], [64830, 64847], [64912, 64913], [64968, 65007],
         [65020, 65135], [65277, 65295], [65306, 65312], [65339, 65344], [65371, 65381],
         [65471, 65473], [65480, 65481], [65488, 65489], [65496, 65497]];
    for (i = 0; i < ranges.length; i++) {
        start = ranges[i][0];
        end = ranges[i][1];
        for (j = start; j <= end; j++) {
            result[j] = true;
        }
    }
    return result;
})();

function splitQuery(query) {
    var result = [];
    var start = -1;
    for (var i = 0; i < query.length; i++) {
        if (splitChars[query.charCodeAt(i)]) {
            if (start !== -1) {
                result.push(query.slice(start, i));
                start = -1;
            }
        } else if (start === -1) {
            start = i;
        }
    }
    if (start !== -1) {
        result.push(query.slice(start));
    }
    return result;
}


