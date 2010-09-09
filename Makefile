all: peg.md.html metacircular.peg bootstrap.js
clean:
	rm peg.md.html metacircular.peg bootstrap.js

# FWIW note that mkhtml.py has its own Make-like mtime-comparison
# logic internally.
%.md.html: %.md mkhtml.py
	./mkhtml.py $<

metacircular.peg: peg.md handaxeweb.lua
	./handaxeweb.lua 'the metacircular compiler-compiler' < $< > $@

bootstrap.js: peg.md handaxeweb.lua
	./handaxeweb.lua 'the bunch-of-functions version' < $< > $@

handaxeweb.lua: handaxeweb.md
	./build_handaxeweb
