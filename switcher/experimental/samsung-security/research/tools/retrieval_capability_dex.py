"""Private ordinary-DEX method locator for the capability leaf; no OEM execution."""
import struct
from build_coloros_settings_rpmb_leaf import header, u16, u32, uleb

def locate(data, wanted_owner, wanted_signature):
    header(data)
    strings,types,protos,ids,classes=(u32(data,p) for p in (60,68,76,92,100))
    def string(index):
        if index>=u32(data,56):raise ValueError('String index')
        p=u32(data,strings+4*index);_,p=uleb(data,p);end=data.find(b'\0',p,min(len(data),p+1048576))
        if end<0:raise ValueError('String bound')
        return data[p:end]
    def typ(index):
        if index>=u32(data,64):raise ValueError('Type index')
        return string(u32(data,types+4*index))
    def signature(index):
        owner,proto,name=struct.unpack_from('<HHI',data,ids+8*index)
        if proto>=u32(data,72):raise ValueError('Proto index')
        ret,params=u32(data,protos+12*proto+4),u32(data,protos+12*proto+8);args=[]
        if params:
            n=u32(data,params)
            if n>65535 or params+4+2*n>len(data):raise ValueError('Parameter extent')
            args=[typ(u16(data,params+4+2*i)) for i in range(n)]
        return string(name)+b'('+b''.join(args)+b')'+typ(ret)
    found=[];ranges=[];encoded=0
    for ci in range(u32(data,96)):
        row=classes+32*ci;owner=u32(data,row);p=u32(data,row+24)
        if not p:continue
        counts=[]
        for _ in range(4):n,p=uleb(data,p);counts.append(n)
        if sum(counts)>2000000:raise ValueError('Member bound')
        for count in counts[:2]:
            index=0
            for _ in range(count):
                delta,p=uleb(data,p);index+=delta;_,p=uleb(data,p)
                if index>=u32(data,80):raise ValueError('Field index')
        for count in counts[2:]:
            index=0
            for _ in range(count):
                delta,p=uleb(data,p);index+=delta;access,p=uleb(data,p);code,p=uleb(data,p);encoded+=1
                if index>=u32(data,88) or u16(data,ids+8*index)!=owner:raise ValueError('Encoded identity')
                if not code:continue
                if code%4 or code+16>len(data):raise ValueError('Code header extent')
                units=u32(data,code+12);start=code+16;end=start+2*units
                if units>1000000 or end>len(data):raise ValueError('Instruction extent')
                ranges.append((index,start,end))
                if typ(owner)==wanted_owner.encode() and signature(index)==wanted_signature.encode():
                    found.append({'methodId':index,'codeOffset':code,'instructionsOffset':start,'instructionUnits':units,'registers':u16(data,code),'incomingWords':u16(data,code+2),'outgoingWords':u16(data,code+4),'tryItems':u16(data,code+6),'debugInfoOffset':u32(data,code+8),'accessFlags':access})
    if len(found)>1:raise ValueError('Ambiguous target')
    if not found:return None,{'encodedMethods':encoded,'codeBodies':len(ranges)}
    f=found[0];aliases=[v for v in ranges if v[0]!=f['methodId'] and max(f['instructionsOffset'],v[1])<min(f['instructionsOffset']+4,v[2])]
    if aliases:raise ValueError('Method code aliases patch')
    return f,{'encodedMethods':encoded,'codeBodies':len(ranges),'otherMethodAliases':0}
