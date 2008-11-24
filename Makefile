all: peg.md.html metacircular.peg
clean:
	rm peg.md.html metacircular.peg

# FWIW note that mkhtml.py has its own Make-like mtime-comparison
# logic internally.
%.md.html: %.md mkhtml.py
	./mkhtml.py $<

metacircular.peg: peg.md handaxeweb.py
	./handaxeweb.py 'the metacircular compiler-compiler' < $< > $@
