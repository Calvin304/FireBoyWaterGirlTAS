import subprocess

def click_swf():
    output = subprocess.run("xdotool getwindowgeometry --shell "
                            "`xdotool search --name 'Adobe Flash Player'`", shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    window_data = dict([item.split("=") for item in output.stdout.decode("utf8").splitlines()])
    window = window_data["WINDOW"]
    width = int(window_data.get("WIDTH", 929))
    height = int(window_data.get("HEIGHT", 1010))

    # first play button
    subprocess.run("xdotool mousemove --window {} {} {}".format(window, width * 0.5, height * 0.8), shell=True)
    subprocess.run("xdotool click 1".format(window), shell=True)
    # second play button
    subprocess.run("xdotool mousemove --window {} {} {}".format(window, width * 0.5, height * 0.55), shell=True)
    subprocess.run("xdotool click 1".format(window), shell=True)
    # move cursor out of the way
    subprocess.run("xdotool mousemove --window {} {} {}".format(window, width, height), shell=True)
    return window