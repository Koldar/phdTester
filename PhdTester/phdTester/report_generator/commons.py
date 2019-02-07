import re


def sanitize_text(text: str) -> str:
    """
    remove risky characters in a latex text file
    :param text:
    :return:
    """

    text = text.replace("%", r"\%")
    text = text.replace("_", r"\_")

    return text


def sanitize_label(text: str) -> str:
    """
    remove risky charactger in a latex label
    :param text:
    :return:
    """
    for c in "%.|_#[]@":
        text = text.replace(c, "-")
    return text


def sanitize_imagename(name: str) -> str:
    """
    remove risky characters in a latex image filename and replace them
    with a non-risky one (-)
    :param name: the image filename to sanitize
    :return: the sanitized filename
    """
    for c in "%.|_#[]@":
        name = name.replace(c, "-")
    return name


def sanitize_caption(caption: str) -> str:
    caption = caption.replace("\n", r"")
    caption = re.sub(r"\s\s*", r" ", caption)
    caption = caption.replace("_", r"\_")
    caption = caption.replace("%", r"\%")
    caption = caption.replace("#", r"\#")
    return caption
