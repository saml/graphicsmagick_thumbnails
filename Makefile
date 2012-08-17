CFLAGS = -I/usr/include/GraphicsMagick -O2
LDFLAGS = -lGraphicsMagick

gm_thumbnails: gm_thumbnails.c
	$(CC) $(CFLAGS) $^ $(LDFLAGS) -o $@

clean: 
	rm -f gm_thumbnails
