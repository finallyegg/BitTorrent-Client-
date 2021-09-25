def encode(bytesString):
    retval = []
    for i in range(len(bytesString)):
        j = int(bytesString[i])
        if(j >= ord('0') and j <= ord('9')) or (j >= ord('a') and j <= ord('z')) or (j >= ord('A') and j <= ord('Z')) or j == ord('.') or \
                j == ord('-') or j == ord('_') or j == ord('~'):
            retval.append(bytesString[i:i+1].decode("utf-8"))
        else:
            retval += ["%", bytes.hex(bytesString[i:i+1])]
    return "".join(retval)
