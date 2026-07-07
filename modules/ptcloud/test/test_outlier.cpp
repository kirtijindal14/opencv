// This file is part of OpenCV project.
// It is subject to the license terms in the LICENSE file found in the top-level directory
// of this distribution and at http://opencv.org/license.html.

#include "test_precomp.hpp"

namespace opencv_test { namespace {

using namespace cv;

// A dense inlier cluster with a handful of far, sparse outliers planted in.
// Any coordinate >= OUTLIER_MIN belongs to a planted outlier, so tests can
// check purely by geometry without any brittle hard-coded gold values.
class OutlierRemovalTest : public testing::Test
{
protected:
    void SetUp() override
    {
        RNG& rng = theRNG();

        nInliers = 2000;
        for (int i = 0; i < nInliers; i++)
            cloud.push_back(Point3f((float)rng.uniform(-1.0, 1.0),
                                    (float)rng.uniform(-1.0, 1.0),
                                    (float)rng.uniform(-0.02, 0.02)));   // thin, dense slab

        nOutliers = 40;
        for (int i = 0; i < nOutliers; i++)
            cloud.push_back(Point3f((float)rng.uniform(5.0, 10.0),
                                    (float)rng.uniform(5.0, 10.0),
                                    (float)rng.uniform(5.0, 10.0)));     // far, sparse floaters
    }

    static bool isPlantedOutlier(const Point3f& p)
    {
        return p.x >= OUTLIER_MIN || p.y >= OUTLIER_MIN || p.z >= OUTLIER_MIN;
    }

    static int countOutliers(const Mat& m)
    {
        int c = 0;
        for (int i = 0; i < (int)m.total(); i++)
            if (isPlantedOutlier(m.at<Vec3f>(i))) c++;
        return c;
    }

public:
    static const int OUTLIER_MIN = 3;
    std::vector<Point3f> cloud;
    int nInliers = 0;
    int nOutliers = 0;
};

TEST_F(OutlierRemovalTest, StatisticalRemovesPlantedOutliers)
{
    Mat out, kept;
    EXPECT_NO_THROW(removeStatisticalOutliers(Mat(cloud), out, 20, 2.0, kept));

    EXPECT_EQ(countOutliers(out), 0);                             // all floaters gone
    EXPECT_GE((int)out.total(), (int)(nInliers * 0.95));          // nearly all inliers kept
    EXPECT_LE((int)out.total(), nInliers + nOutliers);           // never invents points
    EXPECT_EQ((int)kept.total(), (int)out.total());              // one index per kept point
}

TEST_F(OutlierRemovalTest, RadiusRemovesPlantedOutliers)
{
    Mat out, kept;
    EXPECT_NO_THROW(removeRadiusOutliers(Mat(cloud), out, 0.3, 5, kept));

    EXPECT_EQ(countOutliers(out), 0);
    EXPECT_GE((int)out.total(), (int)(nInliers * 0.95));
    EXPECT_LE((int)out.total(), nInliers + nOutliers);
    EXPECT_EQ((int)kept.total(), (int)out.total());
}

TEST_F(OutlierRemovalTest, KeptIndicesMapBackToInput)
{
    Mat out, kept;
    removeStatisticalOutliers(Mat(cloud), out, 20, 2.0, kept);
    ASSERT_EQ((int)kept.total(), (int)out.total());

    for (int i = 0; i < (int)kept.total(); i++)
    {
        int idx = kept.at<int>(i);
        ASSERT_GE(idx, 0);
        ASSERT_LT(idx, (int)cloud.size());
        const Point3f& src = cloud[idx];
        Vec3f dst = out.at<Vec3f>(i);
        EXPECT_FLOAT_EQ(src.x, dst[0]);
        EXPECT_FLOAT_EQ(src.y, dst[1]);
        EXPECT_FLOAT_EQ(src.z, dst[2]);
    }
}

TEST_F(OutlierRemovalTest, EmptyInputIsHandled)
{
    Mat empty(0, 1, CV_32FC3), out;
    EXPECT_NO_THROW(removeStatisticalOutliers(empty, out));
    EXPECT_TRUE(out.empty());
    EXPECT_NO_THROW(removeRadiusOutliers(empty, out, 0.3));
    EXPECT_TRUE(out.empty());
}

}} // namespace
