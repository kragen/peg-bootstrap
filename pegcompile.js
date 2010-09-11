#!/usr/local/bin/node
// This is a script to invoke our bootstrap compiler with node.js
// hooking its input up to stdin and its output up to stdout.
var sys = require('sys');
var Script = process.binding('evals').Script;

var compiler_script_file = process.argv[2];
if (!compiler_script_file) {
    sys.debug("Usage: "+process.argv[1]+" bootstrap.js < foo.peg > foo.js"); // XXX sys.debug is the wrong thing
    process.exit(1);
}

var compiler = require('./' + compiler_script_file);

var stdin = process.openStdin();
var buf = [];
stdin.on('data', function(data) { buf.push(data) });
stdin.on('end', function() {
    sys.print(compiler.parse_grammar(buf.join(''), 0).val);
    stdin.destroy();
});
