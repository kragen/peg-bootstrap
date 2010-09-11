#!/home/kragen/devel/node/build/default/node
// This is a script to invoke our bootstrap compiler with node.js
// hooking its input up to stdin and its output up to stdout.
var sys = require('sys');
var Script = process.binding('evals').Script;

var bootstrap = require('./bootstrap.js');
var compiler = {};
Script.runInNewContext(bootstrap.all_rules, compiler, 'bootstrap rules');
var parse_grammar = compiler.parse_grammar;

var stdin = process.openStdin();
var buf = [];
stdin.on('data', function(data) { buf.push(data) });
stdin.on('end', function() {
    sys.print(parse_grammar(buf.join(''), 0).val);
    stdin.destroy();
});
