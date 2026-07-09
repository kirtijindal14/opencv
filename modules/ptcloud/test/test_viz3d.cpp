// This file is part of OpenCV project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://opencv.org/license.html.

#include "test_precomp.hpp"
#include <opencv2/highgui.hpp>   // updateWindow / waitKey / destroyWindow

namespace opencv_test { namespace {

using namespace cv;

// viz3d is OpenGL/window based. Skip when no GL context can be created
// (e.g. headless CI without a display).
static bool viz3dAvailable()
{
    try
    {
        viz3d::showPoints("viz3d_gl_probe", "p", Mat::zeros(4, 6, CV_32F));
        destroyWindow("viz3d_gl_probe");
        return true;
    }
    catch (const cv::Exception&)
    {
        return false;
    }
}

// Smoke/regression test for the public viz3d API. Exercises every render path
// touched by review fixes and renders a few frames; passes if nothing throws or
// hangs. (The #1 hang is distance-triggered via interactive zoom and can't be
// forced through the public API, so it is covered by a separate math check;
// here the grid is exercised at the default view.)
TEST(Viz3D, render_scene_smoke)
{
    if (!viz3dAvailable())
        throw cvtest::SkipTestException("viz3d/OpenGL not available (no GL context)");

    const String w = "viz3d_test";

    Mat pts(256, 6, CV_32F);
    randu(pts, 0.0f, 1.0f);
    EXPECT_NO_THROW(viz3d::showPoints(w, "pts", pts));
    EXPECT_NO_THROW(viz3d::setGridVisible(w, true));                 // grid -> getGridVertices (#1 site)

    EXPECT_NO_THROW(viz3d::showBox(w, "box", Vec3f::all(1.0f), Vec3f(1, 0, 0)));
    EXPECT_NO_THROW(viz3d::showSphere(w, "sphere", 1.0f, Vec3f(0, 1, 0)));

    // forward = (0,+1,0) and (0,-1,0): the degenerate up-vector case guarded by #4.
    float traj[] = { 0,0,0, 0,1,0,   1,0,0, 0,-1,0 };
    EXPECT_NO_THROW(viz3d::showCameraTrajectory(w, "traj", Mat(2, 6, CV_32F, traj), 1.0f, 0.5f));

    Mat rgbd(16, 16, CV_32FC4, Scalar(120, 120, 120, 500));         // #3 showRGBD path
    EXPECT_NO_THROW(viz3d::showRGBD(w, "rgbd", rgbd, Matx33f(8, 0, 8, 0, 8, 8, 0, 0, 1), 0.1f));

    for (int i = 0; i < 4; ++i)
    {
        EXPECT_NO_THROW(updateWindow(w));
        waitKey(1);
    }

    EXPECT_NO_THROW(viz3d::destroyObject(w, "pts"));
    destroyAllWindows();
}

}} // namespace
