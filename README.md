    make
    ./gm_thumbnails original.jpg -f 1832x1217+0+991+146x97+0+1+70 -o output.jpg


For webapp

    #pip install Flask --user
    python thumbnails.py

Set up [thttpd](http://acme.com/software/thttpd/)

    cd thttpd-src/
    ./configure
    make
    cp thttpd ~/opt/thttpd/

    cd ~/graphicsmagick_thumbnails/
    cp thttpd thttpd-stop ~/bin/
    cp throttles.conf ~/opt/thttpd/

and change thumbnails.py's CDN setting to http://<yourhost>:8081



