import requests, os, sys, math

import time, datetime
from time import gmtime, strftime

# import piexif
import pyexiv2

basicApiUrl = "https://api.vc.bilibili.com/link_draw/v1/doc/upload_count?uid="
apiUrl = (
    "https://api.vc.bilibili.com/link_draw/v1/doc/doc_list?page_size=30&biz=all&uid="
)
headers = {
    "Referer": "https://space.bilibili.com/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36",
}

# Get the amount of all draws
# If error return 0
def getTotalDraw(bid):
    try:
        req = requests.get(basicApiUrl + bid, headers=headers)
        rspJson = req.json()
    except:
        return 0

    if "data" in rspJson and "all_count" in rspJson["data"]:
        return int(rspJson["data"]["all_count"])

    return 0


def downloadAll(bid, totalPage, baseDir):
    # Create drawer's directory
    usrDir = os.path.join(baseDir, bid)
    try:
        os.makedirs(usrDir)
    except:
        pass

    startTime = strftime("%Y_%m_%d_%H_%M_%S", gmtime())
    srcFile = os.path.join(usrDir, "failed.txt")
    with open(srcFile, "w") as failFile:
        startStr = "Last downloaded at {}".format(startTime)
        failFile.write(startStr + "\n")

    for page in range(totalPage):
        downloadDrawList(bid, page, usrDir)

    if sum(1 for line in open(srcFile)) > 1:
        dstFile = os.path.join(usrDir, startTime + "_failed.txt")
        os.system("cp {} {}".format(srcFile, dstFile))
    else:
        print("No failure when downloading images")


# Get the draw list, 30 draws in each page
def downloadDrawList(bid, page, usrDir):
    url = apiUrl + bid

    # Add page num
    url = url + "&page_num=" + str(page)

    try:
        req = requests.get(url, timeout=5, headers=headers)
        rspJson = req.json()

        # Get all items in a range
        items = rspJson["data"]["items"]

        for i in items:
            urls = {}
            did = str(i["doc_id"])

            # convert date from ctime in response
            postDatetime = datetime.datetime.strptime(
                time.ctime(i["ctime"]), "%a %b %d %H:%M:%S %Y"
            )

            desc = i["description"]

            # Single item traversal
            count = 0
            for j in i["pictures"]:
                urls[count] = j["img_src"]
                count += 1

            # Download
            downloadDraw(bid, did, urls, usrDir, postDatetime, desc)
    except Exception as e:
        print(e)
        pass


# https://github.com/LeoHsiao1/pyexiv2/issues/77
def updateMetaTime(imgPath, postDatetime):
    newMetaDate = postDatetime.strftime("%Y:%m:%d %H:%M:%S")

    format = imgPath.split(".")[-1]

    if format == 'png':
        with pyexiv2.Image(imgPath) as img:
            xmp_dict = img.read_xmp()
            img.modify_xmp({'Xmp.xmp.CreateDate': newMetaDate})
        print("MetaTime updated!")
    else:
        with pyexiv2.Image(imgPath) as img:
            exif_dict = img.read_exif()
            if not ('Exif.Photo.DateTimeOriginal' in exif_dict) and not (
                'Exif.Photo.DateTimeDigitized' in exif_dict
            ):
                img.modify_exif(
                    {
                        'Exif.Photo.DateTimeOriginal': newMetaDate,
                        'Exif.Photo.DateTimeDigitized': newMetaDate,
                    }
                )
                print("MetaTime updated!")
            elif ('Exif.Photo.DateTimeOriginal' in exif_dict) and (
                'Exif.Photo.DateTimeDigitized' in exif_dict
            ):
                # small images have exif information
                print("Already has MetaTime!")
                pass
            else:
                if 'Exif.Photo.DateTimeOriginal' in exif_dict:
                    img.modify_exif({'Exif.Photo.DateTimeDigitized': newMetaDate})
                else:
                    img.modify_exif({'Exif.Photo.DateTimeOriginal': newMetaDate})
                print("MetaTime updated!")


def updateMetaTime_piexif(imgPath, postDatetime):
    import piexif

    newMetaDate = postDatetime.strftime("%Y:%m:%d %H:%M:%S")

    exif_dict = piexif.load(imgPath)
    if not (piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]) and not (
        piexif.ExifIFD.DateTimeDigitized in exif_dict["Exif"]
    ):
        exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = newMetaDate
        exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = newMetaDate
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, imgPath)
        print("MetaTime updated!")
    elif (piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]) and (
        piexif.ExifIFD.DateTimeDigitized in exif_dict["Exif"]
    ):
        # small images have exif information
        pass
    else:
        if piexif.ExifIFD.DateTimeOriginal in exif_dict["Exif"]:
            exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = newMetaDate
        else:
            exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = newMetaDate
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, imgPath)
        print("MetaTime updated!")


# Download draws
def downloadDraw(bid, did, urls, usrDir, postDatetime, desc):
    # .strip() only removes the substrings from the string’s start and end position
    postDate = postDatetime.strftime("%Y_%m_%d")
    if len(desc.replace("\n", "")) <= 10:
        subdir = "{}_{}".format(postDate, desc.replace("\n", ""))
    else:
        subdir = "{}_{}".format(postDate, desc.replace("\n", "")[:10])
    subdirPath = os.path.join(usrDir, subdir)
    print("Image saved in", subdirPath)
    if not os.path.exists(subdirPath):
        os.makedirs(subdirPath)

    with open(os.path.join(subdirPath, "description.txt"), "w") as dsec_file:
        dsec_file.write(desc)

    count = 0
    for i in range(len(urls)):
        imgUrl = urls[i]
        # Get image format from url
        suffix = imgUrl.split(".")[-1]

        # File naming
        ## bid: Bilibili user id
        ## did: Draw id
        # v1
        # fileName = did + "_b" + str(count) + "." + suffix
        # v2
        # fileName = "{}_{}_b{}.{}".format(postDate, did, count, suffix)
        fileName = "{}_b{}.{}".format(did, count, suffix)

        imgPath = os.path.join(subdirPath, fileName)

        try:
            if os.path.exists(imgPath):
                print("Skipped " + did + " " + imgUrl)
                updateMetaTime(imgPath, postDatetime)
                count += 1
                continue
            print("Downloading " + did + " " + imgUrl)
            # Download single image
            req = requests.get(imgUrl, timeout=20, headers=headers)
            # Create image file
            with open(imgPath, "wb") as f:
                f.write(req.content)

            # exif manipulation
            updateMetaTime(imgPath, postDatetime)

        except Exception as e:
            print(e)
            print("Fail to download: " + did + " " + imgUrl)

            with open(os.path.join(usrDir, "failed.txt"), "a") as failFile:
                failFile.write(subdir + "\n")
                failFile.write(imgPath + "\n")
                failFile.write(imgUrl + "\n")
        count += 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please enter the bilibili user id.")
        sys.exit(0)

    bid = str(sys.argv[1])

    totalDraw = getTotalDraw(bid)
    totalPage = math.ceil(totalDraw / 30)
    # for page in range(totalPage):
    #     downloadDrawList(bid, page, baseDir="./")
    # downloadAll(bid, totalPage, baseDir="./")
    downloadAll(bid, totalPage, baseDir="/home/he/bili_photos")
