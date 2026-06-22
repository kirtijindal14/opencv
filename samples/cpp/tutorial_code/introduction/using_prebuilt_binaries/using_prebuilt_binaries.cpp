#include <opencv2/opencv.hpp>
#include <iostream>

int main(int argc, char** argv)
{
    cv::Mat image = cv::imread("lena.jpg", cv::IMREAD_COLOR);
    if (image.empty())
    {
        std::cerr << "Error: Could not open or find the image." << std::endl;
        return -1;
    }

    cv::Mat processed_image;
    cv::GaussianBlur(image, processed_image, cv::Size(7, 7), 1.5, 1.5);

    cv::imshow("Original", image);
    cv::imshow("Processed", processed_image);
    cv::waitKey(0);
    return 0;
}
