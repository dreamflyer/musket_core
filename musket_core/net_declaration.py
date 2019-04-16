from collections.abc import Hashable
from musket_core import configloader
from musket_core.utils import load_yaml,save,load
import keras
import musket_core.templating as tp
from musket_core.caches import *
from musket_core import datasets
from builtins import isinstance
layers=configloader.load("layers")
from  musket_core.preprocessing import SplitPreproccessor,SplitConcatPreprocessor
import importlib

def take_input(layers,declarations,config,outputs,linputs,pName,withArgs):

    def a(args):
        return args
    return a

def seq(layers,declarations,config,outputs,linputs,pName,withArgs):

    layers=Layers(config,declarations,{},outputs,linputs,withArgs)
    return layers

def repeat(num):
    def repeat(layers,declarations,config,outputs,linputs,pName,withArgs):
        m=[]
        for v in range(num+1):
            cm=layers.parameters.copy()
            cm["_"]=v+1
            m.append(Layers(config, declarations, cm, outputs, linputs, withArgs))
        return m,num
    return repeat

def split(layers,declarations,config,outputs,linputs,pName,withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    return m


def split_preprocessor(layers,declarations,config,outputs,linputs,pName,withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    
    def buildPreprocessor(inputArg):
        return SplitPreproccessor(inputArg,[x.build(inputArg) for x in m])

    return buildPreprocessor


def split_concact_preprocessor(layers, declarations, config, outputs, linputs, pName, withArgs):
    m = [Layers([v], declarations, {}, outputs, linputs, withArgs) for v in config]

    def buildPreprocessor(inputArg):
        return SplitConcatPreprocessor(inputArg, [x.build(inputArg) for x in m])

    return buildPreprocessor


def seq_preprocessor(layers, declarations, config, outputs, linputs, pName, withArgs):
    m = [Layers([v], declarations, {}, outputs, linputs, withArgs) for v in config]

    def buildPreprocessor(inputArg):
        for x in m:
            inputArg=x.build(inputArg)
        return inputArg

    return buildPreprocessor


def passPreprocessor(layers, declarations, config, outputs, linputs, pName, withArgs):
    def buildPreprocessor(inputArg):
        return inputArg
    return buildPreprocessor


def split_concat(layers, declarations, config, outputs, linputs, pName, withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    return m,keras.layers.Concatenate()

def transform_concat(layers, declarations, config, outputs, linputs, pName, withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    def buildPreprocessor(inputArg):
        if isinstance(inputArg,dict):
            inputArg=[inputArg[x] for x in inputArg]
        rs=[]    
        for i in range(len(m)):
            rs.append(m[i].build(inputArg[i]))
            
        return keras.layers.concatenate(rs)

    return buildPreprocessor


def transform_add(layers, declarations, config, outputs, linputs, pName, withArgs):
    m = [Layers([v], declarations, {}, outputs, linputs, withArgs) for v in config]

    def buildPreprocessor(inputArg):
        if isinstance(inputArg, dict):
            inputArg = [inputArg[x] for x in inputArg]
        rs = []
        for i in range(len(m)):
            rs.append(m[i].build(inputArg[i]))

        return keras.layers.add(rs)

    return buildPreprocessor

def split_add(layers,declarations,config,outputs,linputs,pName,withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    return m,keras.layers.Add()

def split_substract(layers,declarations,config,outputs,linputs,pName,withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    return m,keras.layers.Subtract()

def split_mult(layers,declarations,config,outputs,linputs,pName,withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    return m,keras.layers.Multiply()

def split_min(layers,declarations,config,outputs,linputs,pName,withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    return m,keras.layers.Minimum()

def split_max(layers,declarations,config,outputs,linputs,pName,withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    return m,keras.layers.Maximum()

def split_dot(layers,declarations,config,outputs,linputs,pName,withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    return m,keras.layers.Dot()

def split_dot_normalize(layers,declarations,config,outputs,linputs,pName,withArgs):
    m=[Layers([v], declarations, {}, outputs, linputs,withArgs) for v in config]
    return m,keras.layers.Dot(normalize=True)


builtins={
    "split": split,
    "split-concat": split_concat,
    "split-concatenate": split_concat,
    "split-add": split_add,
    "split-substract": split_substract,
    "split-mult": split_mult,
    "split-min": split_min,
    "split-max": split_max,
    "split-dot": split_dot,
    "split-dot-normalize": split_dot_normalize,
    "seq":seq,
    "input": take_input,
    "cache": cache,
    "disk-cache": diskcache,
    "split-preprocessor": split_preprocessor,
    "split-concat-preprocessor": split_concact_preprocessor,
    "seq-preprocessor": seq_preprocessor,
    "pass": passPreprocessor,
    "transform-concat": transform_concat,
    "transform-add": transform_add
}
for i in range(20):
    builtins["repeat("+str(i)+")"]=repeat(i)
gnum=0
class Layers:

    def __init__(self,layers_yaml,declarations,parameters,outputs=None,linputs=None,withArgs={}):
        global gnum
        layers_yaml=tp.resolveTemplates(layers_yaml,parameters)
        pName = "$input"
        self.layerMap:{str: keras.layers.Layer}={}
        self.layerInputs:{str:[str]} = {}
        self.layerArguments:{str:{str}}={}
        self.layerSequence:[keras.layers.Layer]=[]
        self.name="l"+str(gnum)
        self.parameters=parameters
        gnum=gnum+1
        nums={}
        for layer in layers_yaml:
            if isinstance(layer,str):
                layer={ layer:{} }
            layerImpl=None
            key=list(layer.keys())[0]
            config = layer[key]
            isBuildin=False
            if key in builtins :

                layerImpl =builtins[key](self,declarations,config,outputs,linputs,pName,withArgs)
                if isinstance(layerImpl,list):

                    for i in layerImpl:
                        inputs = pName
                        name = i.name
                        self._add(config, inputs, i, name)
                        #pName = name
                        self.output = name
                        if outputs is not None:
                            self.output = outputs
                    pName = [i.name for i in layerImpl]
                    continue
                if isinstance(layerImpl,tuple):
                    second = layerImpl[1]
                    first=layerImpl[0]
                    if isinstance(second,int):
                        for i in first:
                            inputs = pName
                            name = i.name
                            self._add(config, inputs, i, name)
                            pName = name
                            self.output = name
                            if outputs is not None:
                                self.output = outputs
                        #pName = [i.name for i in first]
                    else:
                        for i in first:
                            inputs = pName
                            name = i.name
                            self._add(config, inputs, i, name)
                            #pName = name
                            self.output = name
                            if outputs is not None:
                                self.output = outputs
                        pName = [i.name for i in first]

                        second=layerImpl[1]
                        self._add({}, pName, second, second.name)
                        self.output = second.name
                        if outputs is not None:
                            self.output = outputs
                        pName=second.name
                    continue

                inputs = pName
                name = self.get_new_name(config, key, layerImpl, nums)
                isBuildin=True
            elif key in declarations:
                decl=declarations[key]
                layerImpl=decl.instantiate(declarations,config)
                if isinstance(config,dict):
                    inputs = config["inputs"] if "inputs" in config else pName
                else:
                    inputs=pName    
                name = self.get_new_name(config, key, layerImpl, nums)
            else:
                if config=="all":
                    layer[key]=[]
                layerImpl = layers.instantiate(layer, True,withArgs)[0]
                if "name" in layer:
                    name = layer["name"]
                elif isinstance(config,dict) and "name" in config:
                    name = config["name"]
                    layerImpl.name = name
                else:
                    if hasattr(layerImpl,"name"):
                        name=layerImpl.name
                    else:
                        name=str(layerImpl)
                        layerImpl.name=name
                if isinstance(config,dict):
                    inputs = config["inputs"] if "inputs" in config else pName
                else:
                    inputs=pName

            if inputs==pName:
                if isinstance(config,list) and not isBuildin:
                    all_refs=True
                    for v in config:
                        if not isinstance(v, Hashable):
                            if isinstance(v,list):
                                for x in config:
                                    if not isinstance(x, str):
                                        all_refs = False
                            else:
                                all_refs = False
                        elif v in self.layerMap or v in linputs:
                            pass
                        else:
                            all_refs=False
                    if all_refs:
                        inputs=config
                    pass
            self._add(config, inputs, layerImpl, name)
            pName=name
            self.output=name
            if outputs is not None:
                self.output=outputs
        pass

    def _add(self, config, inputs, layerImpl, name):
        self.layerMap[name] = layerImpl
        self.layerInputs[name] = inputs
        self.layerArguments[name] = config
        self.layerSequence.append(layerImpl)

    def get_new_name(self, config, key, layerImpl, nums):
        if key in nums:
            num = nums[key]
            nums[key] = nums[key] + 1
        else:
            num = 0
            nums[key] = 1

        if isinstance(config,dict) and "name" in config:
            name = config["name"]
        else:
            name = key + str(num)
        layerImpl.name = name
        return name

    def build(self,inputArgs):
        tensorMap={}
        last=None
        def findInput(name,n):
            if '[' in n:
                si=n.index('[')
                base=n[:si]
                quota=n.index(']')
                num=n[si+1:quota]
                return findInput(name,base)[int(num)]

            if isinstance(inputArgs,dict):
                if name in inputArgs:
                    return inputArgs[name]
                if isinstance(n,Hashable) and n in inputArgs:
                    return inputArgs[n]
            if isinstance(n,Hashable) and n in tensorMap:
                return tensorMap[n]

            if n=="$input":
                return inputArgs
            return None
        for l in self.layerSequence:
            inputs=self.layerInputs[l.name]
            if isinstance(inputs,str):
               inp=findInput(l.name,inputs)
               pass
            else:
               inp=[findInput(l.name,i) for i in inputs]
            if isinstance(inp,tuple) or isinstance(inp,list):
                if len(inp)==1:
                    inp=inp[0]
            if isinstance(inp,dict):
                if "$input" in inp and len(inp)==1:
                    inp=inp["$input"]
            res=l(inp)
            tensorMap[l.name]=res
            last=res
        if isinstance(self.output,str):
            return tensorMap[self.output]
        else:
            return [tensorMap[x] for x in self.output]

    def __call__(self, *args, **kwargs):
        x = args
        if isinstance(args,tuple):
            x = args[0]
        return self.build(x)


class Declaration:

    def __init__(self,declaration_yaml):
        if isinstance(declaration_yaml,dict):
            self.parameters=declaration_yaml["parameters"] if "parameters" in declaration_yaml else []
            self.inputs = declaration_yaml["inputs"] if "inputs" in declaration_yaml else []
            self.outputs = declaration_yaml["outputs"] if "outputs" in declaration_yaml else None
            self.body = declaration_yaml["body"] if "body" in declaration_yaml else []
            self.shared = declaration_yaml["shared"] if "shared" in declaration_yaml else False
            self.withArgs = declaration_yaml["with"] if "with" in declaration_yaml else {}
            self.layers=None
        else:
            self.parameters=[]
            self.body=declaration_yaml
            self.outputs=None
            self.inputs=[]
            self.withArgs ={}
            self.shared=False
            self.layers = None

    def instantiate(self, dMap, parameters=None):
        if self.shared:
            if self.layers is not None:
                def am(args):
                    return self.layers(args)
                return am
        if parameters is None:
            parameters={}
        if "args" in parameters:
            parameters=parameters["args"]
        if isinstance(parameters,list):
            pMap={}
            for p in range(len(self.parameters)):
                pMap[self.parameters[p]]=parameters[p]
            parameters=pMap
        l=Layers(self.body,dMap,parameters,self.outputs,self.inputs,self.withArgs)
        if self.shared:
            self.layers=l
        return l


class Declarations:

    def __init__(self,declarations_yaml):
        self.declarationMap:{str:Declaration}={ x:Declaration(declarations_yaml[x]) for x in declarations_yaml}
        pass

    def __contains__(self, item):
        return item in self.declarationMap

    def __getitem__(self, item):
        return self.declarationMap[item]

    def instantiate(self,name,inputs):
        if isinstance(name,list):
            v=Declaration(name).instantiate(self)
            inp=[]
        elif isinstance(name,dict):
            v=Declaration([name]).instantiate(self)
            inp=[]
        else:
            v=self[name].instantiate(self)
            inp=self[name].inputs
        if len(inp)>0:
            if isinstance(inputs,list):
                pMap = {}
                for p in range(len(inp)):
                    pMap[inp[p]] = inputs[p]
                inputs=pMap
                pass
            if isinstance(inputs, dict):
                pass
        else:
            inputs={"$input":inputs}
        return v.build(inputs)

    def model(self,name,inputs):
        m=self.instantiate(name,inputs)
        return keras.Model(inputs,m)

    def preprocess(self,name,inputs):
        return self.instantiate(name,inputs)


def create_model(path,inputs,name="net")->keras.Model:
    n=load_yaml(path)
    d=Declarations(n["declarations"])
    out=d.model(name, inputs)
    return out

def get_declarations(path)->keras.Model:
    n=load_yaml(path)
    d=Declarations(n["declarations"])
    return d


def create_model_from_config(n,inputs,name="net",imports=[])->keras.Model:
    d=Declarations(n)
    for x in imports: layers.register(x)
    out=d.model(name, inputs)
    return out

def create_preprocessor_from_config(n,inputs,name="net",imports=[]):
    d=Declarations(n)    
    for x in imports: layers.register(x)
    if hasattr(inputs,"_preprocessed"):
        return inputs
    if isinstance(inputs,datasets.SubDataSet):
        if hasattr(inputs.ds, "_preprocessed"):
            return inputs

    out=d.preprocess(name, inputs)

    out._preprocessed=True
    return out

DEFAULT_DATASET_DIR=None
def create_dataset_from_config(n,name="net",imports=[]):

    compositeDS = None
    if isinstance(name,dict):
        holdout = extract_datasets(n, imports, name, 'holdout')
        train = extract_datasets(n, imports, name, 'train')
        validation = extract_datasets(n, imports, name, 'validation')

        valDSCount = len(validation)
        trainDSCount = len(train)
        holdoutDSCount = len(holdout)

        if valDSCount + trainDSCount + holdoutDSCount > 0:
            lt = sum([len(x) for x in train])
            lv = sum([len(x) for x in validation])
            lh = sum([len(x) for x in holdout])

            tOff = 0
            vOff = lt
            hOff = lt + lv

            components = [ds for dsList in [train, validation, holdout] for ds in dsList]
            compositeDS = datasets.CompositeDataSet(components)


            if valDSCount > 0 :
                trainIndices      = np.array([i for i in range(tOff, tOff + lt)], dtype=np.int)
                validationIndices = np.array([i for i in range(vOff, vOff + lv)], dtype=np.int)
                compositeDS.folds = [(trainIndices,validationIndices)]

            if holdoutDSCount > 0:
                holdoutIndices    = np.array([i for i in range(hOff, hOff + lh)], dtype=np.int)
                compositeDS.holdoutArr = holdoutIndices

            resultName = []
            if trainDSCount >0:
                resultName.append("t-" + "_".join([x.name for x in train]))
            if valDSCount >0:
                resultName.append("v-" + "_".join([x.name for x in validation]))
            if holdoutDSCount >0:
                resultName.append("h-" + "_".join([x.name for x in holdout]))

            compositeDS.name = "_".join(resultName)

    if compositeDS is not None:
        return compositeDS

    if DEFAULT_DATASET_DIR is not None:
        os.chdir(str(DEFAULT_DATASET_DIR))
    d=Declarations(n)
    for x in imports: layers.register(x)
    out=d.preprocess(name, None)
    out.name=str(name)
    return out

def extract_datasets(decls, imports, d:dict, name:str)->[]:
    result = []
    if name in d:
        ds = d[name]
        if isinstance(ds, dict):
            for n in ds:
                val = ds[n]
                ch = {n: val}
                res1 = create_dataset_from_config(decls, ch, imports)
                result.append(res1)
    return result

def create_test_time_aug(name,imports=[]):
    for x in imports:
        mod=importlib.import_module(x)
        if hasattr(mod,name):
            return getattr(mod,name)
    return None

def create_dataset_transformer(name,imports=[]):
    for x in imports:
        mod=importlib.import_module(x)
        if hasattr(mod,name):
            return getattr(mod,name)
    return None
