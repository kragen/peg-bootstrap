all: peg.md.html metacircular.peg bootstrap.js output.js
clean:
	rm peg.md.html metacircular.peg bootstrap.js output.js

# FWIW note that mkhtml.py has its own Make-like mtime-comparison
# logic internally.
%.md.html: %.md mkhtml.py
	./mkhtml.py $<

metacircular.peg: peg.md handaxeweb.py
	./handaxeweb.py 'the metacircular compiler-compiler' < $< > $@

bootstrap.js: peg.md handaxeweb.py
	./handaxeweb.py 'the bunch-of-functions version' < $< > $@

output.js: peg.md handaxeweb.py
	./handaxeweb.py $@ < $< > $@
