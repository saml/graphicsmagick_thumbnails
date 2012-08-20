#include <magick/api.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

typedef enum ResizeMethods {
    Thumbnail = 0,
    Scale,
    Sample,
    /* Resize */
    Point,
    Box,
    Triangle,
    Hermite,
    Hanning,
    Hamming,
    Blackman,
    Gaussian,
    Quadratic,
    Cubic,
    Catrom,
    Mitchell,
    Lanczos,
    Bessel,
    Sinc
} ResizeMethods;

FilterTypes get_filter(ResizeMethods const resize) {
    switch (resize) {
    case Point:
        return PointFilter;
    case Box:
        return BoxFilter;
    case Triangle:
        return TriangleFilter;
    case Hermite:
        return HermiteFilter;
    case Hanning:
        return HanningFilter;
    case Hamming:
        return HammingFilter;
    case Blackman:
        return BlackmanFilter;
    case Gaussian:
        return GaussianFilter;
    case Quadratic:
        return QuadraticFilter;
    case Cubic:
        return CubicFilter;
    case Catrom:
        return CatromFilter;
    case Mitchell:
        return MitchellFilter;
    case Lanczos:
        return LanczosFilter;
    case Bessel:
        return BesselFilter;
    case Sinc:
        return SincFilter;
    default:
        return UndefinedFilter;
    }

    return UndefinedFilter;
}

Image* generate_rendition(Image *const image, ImageInfo const*image_info, char const* spec, char const* rendition_path, ExceptionInfo *exception) {
    unsigned long crop_x;
    unsigned long crop_y;
    unsigned long crop_width;
    unsigned long crop_height;
    unsigned long width;
    unsigned long height;
    unsigned int quality;
    unsigned int resize;
    double blur;
    unsigned int is_progressive;
    Image const* cropped;
    Image *resized;
    RectangleInfo geometry;
    FilterTypes filter;
    ImageInfo *rendition_info;

    if (sscanf(spec, "%lux%lu+%lu+%lu+%lux%lu+%u+%lf+%u+%u", &crop_width, &crop_height, &crop_x, &crop_y, &width, &height, &resize, &blur, &quality, &is_progressive)) {
        if (width > 0 && height > 0) {
            if (crop_width > 0 && crop_height > 0) {
                geometry.x = crop_x;
                geometry.y = crop_y;
                geometry.width = crop_width;
                geometry.height = crop_height;
                cropped = CropImage(image, &geometry, exception);
                if (!cropped) {
                    CatchException(exception);
                    return NULL;
                }
            } else {
                cropped = image;
            }

            filter = get_filter(resize);

            switch (resize) {
            case Sample:
                resized = SampleImage(cropped, width, height, exception);
                break;
            case Scale:
                resized = ScaleImage(cropped, width, height, exception);
                break;
            case Thumbnail:
                resized = ThumbnailImage(cropped, width, height, exception);
                break;
            case Point:
            case Box:
            case Triangle:
            case Hermite:
            case Hanning:
            case Hamming:
            case Blackman:
            case Gaussian:
            case Quadratic:
            case Cubic:
            case Catrom:
            case Mitchell:
            case Lanczos:
            case Bessel:
            case Sinc:
                resized = ResizeImage(cropped, width, height, filter, blur, exception);
                break;
            }

            if (!resized) {
                CatchException(exception);
                return NULL;
            }


            rendition_info = CloneImageInfo(image_info);
            rendition_info->quality = quality;
            strncpy(resized->filename, rendition_path, MaxTextExtent);
            
            if (is_progressive) {
                rendition_info->interlace = LineInterlace;    
                printf("progressive: %s\n", rendition_path);
            }

            if (!WriteImage(rendition_info, resized)) {
                CatchException(exception);
                DestroyImageInfo(rendition_info);
                return NULL;
            }
            printf("wrote %s\n", resized->filename);
            
            DestroyImageInfo(rendition_info);
            return resized;

        }
        
    }

    return NULL;
}

int main(int argc, char *argv[]) {
    char *original_image_path;
    char rendition_spec[MaxTextExtent] = {0};
    int is_rendition_generated = 0;
    
    int return_code = 0;
    int image_magick_started = 0;

    char opt;
    char const* usage = 
        "Usage: %s <original_image_path> -f <crop_width>x<crop_height>+<crop_x>+<crop_y>+<resize_width>x<resize_height>+<resize_method>+<blur>+<quality>+<progressive> -o <output> [-f ... -o ...]\n"
        "normally, use 0 for resize_method, and 1 for blur.\n"
        "progressive 80%% compression 0.5 blur 300x200 thumbnail: -f 2592x1728+0+311+300x200+0+0.5+80+1\n"
        "non progressive 70%% compression 1.0 blur 300x200 thumbnail: -f 2592x1728+0+311+300x200+0+1+70+0\n"
        ;
    
    Image *original_image;
    Image *rendition;
    ImageInfo *image_info;
    ExceptionInfo exception;

    if (argc < 2) {
        fprintf(stderr, "Need input image path\n"); 
        fprintf(stderr, usage, argv[0]); 
        return -1;
    }

    original_image_path = argv[1];

    /* start image magick */
    InitializeMagick(*argv);
    GetExceptionInfo(&exception);
    image_info = CloneImageInfo((ImageInfo*) NULL);
    image_magick_started = 1;

    /* load original */
    strncpy(image_info->filename, original_image_path, MaxTextExtent);
    image_info->filename[MaxTextExtent-1] = '\0';
    original_image = ReadImage(image_info, &exception);
    if (!original_image) {
        CatchException(&exception);
        fprintf(stderr, "%s\n", exception.reason);
        return_code = -1;
        goto CLEANUP;
    }

    printf("Loaded: %s\n", original_image_path);

    optind = 2;
    while ((opt = getopt(argc, argv, "f:o:")) != -1) {
        switch (opt) {
            case 'o':
                if (!generate_rendition(original_image, image_info, rendition_spec, optarg, &exception)) {
                    fprintf(stderr, "%s : during %s -> %s (%s)\n", exception.reason, original_image_path, rendition_spec, optarg);
                }
                break;
            case 'f':
                strncpy(rendition_spec, optarg, MaxTextExtent);
                break;
            default:
                fprintf(stderr, usage, argv[0]);
                return -1;
        }
    }


CLEANUP:
    if (!image_magick_started) {
        goto RETURN;
    }

    DestroyImageInfo(image_info);
    DestroyExceptionInfo(&exception);
    DestroyMagick();
RETURN:
    return return_code;
}
