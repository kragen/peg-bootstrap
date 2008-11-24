all: peg.md.html
clean:
	rm peg.md.html

# FWIW note that mkhtml.py has its own Make-like mtime-comparison
# logic internally.
%.md.html: %.md mkhtml.py
	./mkhtml.py $<
