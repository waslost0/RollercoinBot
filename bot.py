import os
import random
import time
import datetime
import math
import sys

import numpy
import cv2
import keyboard
import pyautogui
import shutil
from PIL import ImageGrab
from MTM import matchTemplates
from threading import Thread

GAME_NUM = 0
START_TIME = datetime.datetime.now()


def notInList(results, thresholdDist, newObject):
    for result in results:
        if isinstance(result[1], tuple):
            tupleObject = result[1]
            if math.hypot(newObject[0] - tupleObject[0], newObject[1] - tupleObject[1]) < thresholdDist:
                return False
        else:
            if math.hypot(newObject[0] - result[0], newObject[1] - result[1]) < thresholdDist:
                return False

    return True


def isInList(count, coin_item):
    for counter in count:
        if counter[0] == coin_item:
            return True
    return False


def countItemValue(count):
    valuecount = 0
    for counter in count:
        valuecount += counter[1]

    return valuecount


def matchTemplate(screen, template, templateName):
    matches = []
    thresholdDist = 30

    match = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    locations = numpy.where(match >= .7)
    for location in zip(*locations[::-1]):
        if len(matches) == 0 or notInList(matches, thresholdDist, location):
            matches.append((templateName, location))

    return matches


def mouse_click(x, y, wait=0.2):
    pyautogui.click(x, y)
    time.sleep(wait)


def screen_grab():
    im = ImageGrab.grab()
    img_name = os.getcwd() + "\\imgs\\full_snap__" + str(int(time.time())) + ".png"
    im.save(img_name, "PNG")
    return img_name


def find_image(image_path, root_image_path):
    matches = matchTemplates(
        [("img", cv2.imread(image_path))],
        cv2.imread(root_image_path),
        N_object=10,
        score_threshold=0.9,
        # maxOverlap=0.25,
        searchBox=None)
    if len(matches["BBox"]) == 0:
        return None, None
    else:
        box = matches["BBox"][0]
        return box[0], box[1]


def check_image(img, thread=False, self=None):
    if thread:
        while self.game_status == "running":
            b, _ = find_image(img, screen_grab())
            if not b is None:
                self.game_status = "ended"
    else:
        b, _ = find_image(img, screen_grab())
        return True if b is not None else False


def click_image(img):
    time.sleep(0.1)
    x, y = find_image(img, screen_grab())
    if x is None or y is None:
        return

    im = cv2.imread(img)
    t_cols, t_rows, _ = im.shape
    mouse_click(x + t_rows * (3 / 5), y + t_cols * (2 / 3))


def setup():
    try:
        os.mkdir('imgs')
    except FileExistsError:
        print("Program was not correctly closed last time. Make sure to exit the game with CTRL+C")


def start_game(self, start_img_path):
    self.game_status = "starting"

    click_image(start_img_path)
    time.sleep(3)
    retries = 0
    while not check_image("rc_items/start_game.png"):
        retries += 1
        if check_image("rc_items/captcha_error.png") or retries >= 50:
            print('captcha_error')
            keyboard.press_and_release('F5')
            break
        time.sleep(1)

    if not check_image("rc_items/start_game.png"):
        pyautogui.moveTo(100, 100)
        return True
    sx, sy = find_image("rc_items/start_game.png", screen_grab())
    mouse_click(sx + 2, sy + 2, wait=0.1)
    return False


def start_game_msg(name):
    global GAME_NUM
    print("Starting Game #{!s}: '{}'@{!s}".format(GAME_NUM, name, datetime.datetime.now().time()))
    GAME_NUM += 1


def end_game(self, fail=False):
    if not fail:
        self.game_status = "idle"

        keyboard.press_and_release("page up")
        keyboard.press_and_release("down")

        while not check_image("rc_items/gain_power.png"):
            if check_image("rc_items/gain_power_error.png"):
                click_image("rc_items/gain_power_error.png")
                break
            time.sleep(1)
        click_image("rc_items/gain_power.png")

        time.sleep(3)

        keyboard.press_and_release("page up")
        time.sleep(2)
        click_image("rc_items/goto_games.png")
        time.sleep(2)

        if check_image("rc_items/collect_pc.png"):
            click_image("rc_items/click_image")
    else:
        keyboard.press_and_release("page up")
        time.sleep(2)

        click_image("rc_items/goto_games.png")

        os.execv(sys.executable, ['python'] + sys.argv)  # restart script


class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,
                 args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None

    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,
                                        **self._kwargs)

    def join(self, *args):
        Thread.join(self, *args)
        return self._return


class Bot2048:
    def __init__(self):
        self.start_img_path = "rc_items/2048_gameimg.png"
        self.available_moves = ["right", "left", "up", "down"]
        self.game = "2048"
        self.game_status = "idle"

    def can_start(self):
        return check_image(self.start_img_path)

    def play(self):
        err = start_game(self, self.start_img_path)
        if err:
            return not err
        start_game_msg(self.game)
        self.run_game()
        end_game(self)

    def run_game(self):
        self.game_status = "running"

        try:
            thread = ThreadWithReturnValue(target=check_image,
                                           args=("rc_items/gain_power.png", True, self,))
            thread.start()
        except:
            print("Unable to start thread for checking image")
            end_game(self, fail=True)

        while self.game_status == "running":
            for i in range(8):
                keyboard.press_and_release(random.choice(self.available_moves))
                time.sleep(0.15)
            keyboard.press_and_release("page up")  # to prevent errors for the thread with check image


class BotCoinFlip:
    def __init__(self):
        self.start_img_path = "rc_items/coinflip_gameimg.png"
        self.game = "CoinFlip"
        self.game_status = "idle"
        self.coin_pos = []
        self.coin_items = {
            "binance": [],
            "btc": [],
            "eth": [],
            "litecoin": [],
            "monero": [],
            "eos": [],
            "rlt": [],
            "xrp": [],
            "xml": [],
            "tether": [],
        }
        self.coin_images = [
            ("binance", cv2.imread("rc_items/coinflip_item_binance.png")),
            ("btc", cv2.imread("rc_items/coinflip_item_btc.png")),
            ("eth", cv2.imread("rc_items/coinflip_item_eth.png")),
            ("litecoin", cv2.imread("rc_items/coinflip_item_litecoin.png")),
            ("monero", cv2.imread("rc_items/coinflip_item_monero.png")),
            ("eos", cv2.imread("rc_items/coinflip_item_eos.png")),
            ("rlt", cv2.imread("rc_items/coinflip_item_rlt.png")),
            ("xrp", cv2.imread("rc_items/coinflip_item_xrp.png")),
            ("xml", cv2.imread("rc_items/coinflip_item_xml.png")),
            ("tether", cv2.imread("rc_items/coinflip_item_tether.png")),
        ]
        self.card_image = [("card", cv2.imread("rc_items/coinflip_back.png"))]

    def can_start(self):
        return check_image(self.start_img_path)

    def play(self):
        err = start_game(self, self.start_img_path)
        if err:
            return False
        start_game_msg(self.game)

        pyautogui.moveTo(100, 100)
        keyboard.press_and_release("down")
        time.sleep(4)

        self.get_coin_fields()
        self.check_coins()
        self.match_coins()
        end_game(self)
        return True

    def get_coin_fields(self):
        self.game_status = "running"

        screen = cv2.imread(screen_grab())
        matches = cv2.matchTemplate(screen, cv2.imread("rc_items/coinflip_back.png"), cv2.TM_CCOEFF_NORMED)

        locations = numpy.where(matches >= .7)

        append = self.coin_pos.append
        thresholdDist = 30

        for pt in zip(*locations[::-1]):
            if len(self.coin_pos) == 0 or notInList(self.coin_pos, thresholdDist, pt):
                append(pt)

    def check_coins(self):
        ind = 0
        max_index = len(self.coin_pos)
        while ind < max_index:
            coin1_pos = self.coin_pos[ind]
            coin2_pos = self.coin_pos[ind + 1]

            mouse_click(coin1_pos[0] + 10, coin1_pos[1] + 10, wait=0.4)
            mouse_click(coin2_pos[0] + 10, coin2_pos[1] + 10, wait=0.5)

            # pyautogui.moveTo(100, 100)
            screen = cv2.imread(screen_grab())

            matches = []
            threads = []
            i = 1

            for template in self.coin_images:
                try:
                    thread = ThreadWithReturnValue(target=matchTemplate,
                                                   args=(screen, template[1], template[0],))
                    thread.start()
                    threads.append(thread)
                    # print("starting thread " + str(i) + " for matching " + template[0])
                    i += 1
                except:
                    print("Couldn't start thread " + str(i) + " for matching " + template[0])
                    end_game(self, fail=True)

            for thread in threads:
                result = thread.join()
                if len(result) > 0:
                    matches.append(result)

            if len(matches) == 2:
                coin1 = (matches[0][0][0], matches[0][0][1])
                coin2 = (matches[1][0][0], matches[1][0][1])

                if coin1[0] == coin2[0]:
                    self.coin_items.pop(coin1[0])
                else:
                    self.coin_items[coin1[0]].append(coin1[1])
                    self.coin_items[coin2[0]].append(coin2[1])
            else:
                if len(matches) == 1:
                    coin = (matches[0][0][0], matches[0][0][1])
                    self.coin_items.pop(coin[0])
                else:
                    end_game(self, fail=True)

            ind += 2

    def match_coins(self):
        for coin in self.coin_items.values():
            if len(coin) == 2:
                c1 = coin[0]
                mouse_click(c1[0] + 10, c1[1] + 10, wait=0.05)

                c2 = coin[1]
                mouse_click(c2[0] + 10, c2[1] + 10, wait=0.05)
                time.sleep(2)

        keyboard.press_and_release("esc")


class BotCoinClick:
    def __init__(self):
        self.start_img_path = "rc_items/coinclick_gameimg.png"
        self.game = "CoinClick"
        self.game_status = "idle"

    def can_start(self):
        return check_image(self.start_img_path)

    def play(self):
        err = start_game(self, self.start_img_path)
        if err:
            return not err
        start_game_msg(self.game)
        self.run_game()
        end_game(self)

    def run_game(self):
        self.game_status = "running"

        try:
            thread = ThreadWithReturnValue(target=check_image,
                                           args=("rc_items/gain_power.png", True, self,))
            thread.start()
        except:
            print("Unable to start thread for checking image")
            end_game(self, fail=True)

        while self.game_status == "running":
            pic = pyautogui.screenshot(region=(530, 430, 828, 417,))
            width, height = pic.size
            for x in range(0, width, 5):
                for y in range(0, height, 5):
                    r, g, b = pic.getpixel((x, y))

                    # blue coin
                    if b == 183 and r == 0:
                        mouse_click(x + 530, y + 440, wait=0)
                        break

                    # yellow coin
                    if b == 64 and r == 200:
                        mouse_click(x + 530, y + 440, wait=0)
                        break

                    # orange coin
                    if b == 33 and r == 231:
                        mouse_click(x + 530, y + 440, wait=0)
                        break

                    # grey coin
                    if b == 230 and r == 230:
                        mouse_click(x + 535, y + 440, wait=0)
                        break

                    if self.game_status == "ended":
                        break
                if self.game_status == "ended":
                    break


def main():
    Bots = [
        Bot2048,
        BotCoinFlip,
        BotCoinClick
    ]
    global GAME_NUM
    while True:
        for bot in Bots:
            if bot().can_start():
                bot().play()


if __name__ == "__main__":
    # pyautogui.displayMousePosition()

    if os.path.exists("imgs"):
        shutil.rmtree('imgs')
    setup()
    try:
        main()
    except KeyboardInterrupt:
        print("Program closed by User!")

    finally:
        print("\nStatistics:\n",
              "Time running: {!s}\n".format(datetime.datetime.now() - START_TIME),
              "Played Games:  {!s}\n".format(GAME_NUM)
              )
        shutil.rmtree('imgs')
