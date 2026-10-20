package edu.northwestern.lookagain.wildcatverify

import edu.northwestern.lookagain.wildcatverify.autolabel.Box
import edu.northwestern.lookagain.wildcatverify.autolabel.ImageHash
import edu.northwestern.lookagain.wildcatverify.autolabel.ImageNode
import edu.northwestern.lookagain.wildcatverify.autolabel.PhotoFinder
import edu.northwestern.lookagain.wildcatverify.autolabel.PixelPhotoFinder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PhotoFinderTest {
    private val screen = Box(0, 0, 1080, 2400)
    private val density = 2.625f // 420 dpi phone

    private fun image(box: Box, className: String = "android.widget.ImageView", visible: Boolean = true) = ImageNode(className, box, visible)

    @Test fun keepsPostPhotos() {
        val photo = Box(40, 600, 1040, 1300)
        assertEquals(listOf(photo), PhotoFinder.select(listOf(image(photo)), screen, density))
    }

    @Test fun skipsAvatarsAndIcons() {
        val avatar = Box(40, 400, 150, 510) // 42 dp
        assertTrue(PhotoFinder.select(listOf(image(avatar)), screen, density).isEmpty())
    }

    @Test fun skipsPhotosCutOffByTheScreenEdge() {
        val clipped = Box(40, 0, 1040, 500)
        val bottom = Box(40, 1900, 1040, 2400)
        assertTrue(PhotoFinder.select(listOf(image(clipped), image(bottom)), screen, density).isEmpty())
    }

    @Test fun skipsHiddenAndNonImageNodes() {
        val box = Box(40, 600, 1040, 1300)
        assertTrue(PhotoFinder.select(listOf(image(box, visible = false), image(box, "android.view.ViewGroup")), screen, density).isEmpty())
    }

    @Test fun readsWebImagesInChrome() {
        val box = Box(40, 600, 1040, 1300)
        assertEquals(1, PhotoFinder.select(listOf(image(box, "android.widget.Image")), screen, density).size)
    }

    @Test fun mergesWrapperAndInnerImage() {
        val outer = Box(40, 600, 1040, 1300)
        val inner = Box(42, 602, 1038, 1298)
        assertEquals(listOf(outer), PhotoFinder.select(listOf(image(inner), image(outer)), screen, density))
    }

    @Test fun ordersTopToBottomAndCaps() {
        val boxes = (0 until 8).map { Box(40 + (it % 2) * 520, 200 + (it / 2) * 450, 520 + (it % 2) * 520, 600 + (it / 2) * 450) }
        val selected = PhotoFinder.select(boxes.map { image(it) }, screen, density)
        assertEquals(PhotoFinder.MAX_PHOTOS, selected.size)
        assertEquals(selected.sortedWith(compareBy({ it.top }, { it.left })), selected)
    }
}

class ImageHashTest {
    private fun gradient(shift: Int) = IntArray(72) { i ->
        val v = ((i % 9) * 28 + (i / 9) * 3 + shift).coerceIn(0, 255)
        (0xFF shl 24) or (v shl 16) or (v shl 8) or v
    }

    @Test fun samePixelsSameHash() {
        assertEquals(ImageHash.dHash(gradient(0)), ImageHash.dHash(gradient(0)))
    }

    @Test fun brightnessShiftBarelyMatters() {
        assertTrue(ImageHash.distance(ImageHash.dHash(gradient(0)), ImageHash.dHash(gradient(10))) <= 5)
    }

    @Test fun differentImagesDiffer() {
        val reversed = gradient(0).reversedArray()
        assertTrue(ImageHash.distance(ImageHash.dHash(gradient(0)), ImageHash.dHash(reversed)) > 20)
    }
}

class PixelPhotoFinderTest {
    private val density = 2.625f
    private val width = 540
    private val height = 1200
    private val screen = Box(0, 0, 1080, 2400)

    /** A light feed: white background, a few lines of "text", and one noisy photo block. */
    private fun feed(photo: Box?): IntArray {
        val random = java.util.Random(1)
        val pixels = IntArray(width * height) { 0xFFFFFFFF.toInt() }
        // Sparse dark text strokes, like post text.
        for (y in 300 until 330) for (x in 30 until 500) if ((x / 3 + y) % 7 == 0) pixels[y * width + x] = 0xFF111111.toInt()
        if (photo != null) {
            for (y in photo.top until photo.bottom) for (x in photo.left until photo.right) {
                pixels[y * width + x] = (0xFF shl 24) or (random.nextInt(0xFFFFFF))
            }
        }
        return pixels
    }

    @Test fun findsAPhotoBlock() {
        val found = PixelPhotoFinder.find(feed(Box(20, 400, 520, 760)), width, height, 0.5f, screen, density)
        assertEquals(1, found.size)
        val box = found[0]
        assertTrue("$box", kotlin.math.abs(box.left - 40) <= 16 && kotlin.math.abs(box.top - 800) <= 16)
        assertTrue("$box", kotlin.math.abs(box.right - 1040) <= 16 && kotlin.math.abs(box.bottom - 1520) <= 16)
    }

    @Test fun ignoresTextAndBackground() {
        assertTrue(PixelPhotoFinder.find(feed(null), width, height, 0.5f, screen, density).isEmpty())
    }

    @Test fun ignoresSmallBlocksLikeAvatars() {
        assertTrue(PixelPhotoFinder.find(feed(Box(20, 400, 60, 440)), width, height, 0.5f, screen, density).isEmpty())
    }

    @Test fun findsPhotosOnDarkBackgrounds() {
        val pixels = feed(Box(20, 400, 520, 760)).map { if (it == 0xFFFFFFFF.toInt()) 0xFF000000.toInt() else it }.toIntArray()
        assertEquals(1, PixelPhotoFinder.find(pixels, width, height, 0.5f, screen, density).size)
    }
}

class MotionTest {
    @Test fun smallChangesAreNotScrolling() {
        val a = IntArray(27 * 60) { it % 255 }
        val b = a.copyOf().also { for (i in 0 until 40) it[i] = 255 - it[i] }
        assertTrue(edu.northwestern.lookagain.wildcatverify.autolabel.ScreenLabelService.changedShare(a, b) < 0.12)
    }

    @Test fun shiftedScreenIsScrolling() {
        val a = IntArray(27 * 60) { (it * 37) % 255 }
        val b = IntArray(a.size) { a[(it + 27 * 6) % a.size] }
        assertTrue(edu.northwestern.lookagain.wildcatverify.autolabel.ScreenLabelService.changedShare(a, b) > 0.12)
    }
}
