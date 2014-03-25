import array
import base64
import logging
import struct

logger = logging.getLogger('confluence.shortcode')

def url2id(shortcode):
    try:
        decoded = array.array('b', base64.b64decode(shortcode))
        logger.debug("Decoded %s into %s", shortcode, decoded)
        decoded.fromlist([0] * (8 - len(decoded)))
        logger.debug("Ensuring length of 8: %s", decoded)
        return struct.unpack_from('L', decoded)[0]
    except (struct.error, TypeError) as e:
        logger.exception("Failed to decode")
        raise ValueError('Unable to decode shortcode into id number')

def id2url(page_id):
    try:
        b64 = base64.b64encode(array.array('b',
                                           struct.pack('L', long(page_id))))
        return b64.rstrip('A=')
    except struct.error as e:
        logger.exception("Failed to encode %d", page_id)
        raise ValueError('Unable to encode as shortcode: id too large')
