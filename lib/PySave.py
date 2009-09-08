def save(obj, file):
    import pickle
    import os.path

    fileobj = open(file, "w")
    pickle.dump(obj, fileobj)
    fileobj.close()

def load(file):
    import pickle
    import os.path

    if not os.path.isfile(file):
        return None

    fileobj = open(file)
    obj = pickle.load(fileobj)
    fileobj.close()

    if hasattr(obj, "init"):
        obj.init()

    return obj
    


