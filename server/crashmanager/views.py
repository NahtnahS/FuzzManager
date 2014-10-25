from rest_framework import viewsets
from crashmanager.serializers import BucketSerializer, CrashEntrySerializer
from crashmanager.models import CrashEntry, Bucket
from django.template.context import RequestContext
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.ProgramConfiguration import ProgramConfiguration
from django.core.exceptions import SuspiciousOperation
from django.db.models import Q
from django.db.models.aggregates import Count

def logout_view(request):
    logout(request)
    # Redirect to a success page.

@login_required(login_url='/login/')
def index(request):
    return redirect('crashmanager:crashes')

@login_required(login_url='/login/')
def signatures(request):
    entries = Bucket.objects.annotate(size=Count('crashentry'))
    context = RequestContext(request, { 'siglist' : entries })
    return render(request, 'signatures.html', context)

@login_required(login_url='/login/')
def crashes(request):
    entries = CrashEntry.objects.filter(bucket=None)
    context = RequestContext(request, { 'crashlist' : entries })
    return render(request, 'crashes.html', context)

@login_required(login_url='/login/')
def newSignature(request):
    if request.method == 'POST':
        #TODO: FIXME: Update bug here as well
        bucket = Bucket(signature=request.POST['signature'], 
                            shortDescription=request.POST['shortDescription'])
        
        bucket.save()
        return redirect('crashmanager:sigview', sigid=bucket.pk)
    elif request.method == 'GET':
        if 'crashid' in request.GET:
            crashEntry = get_object_or_404(CrashEntry, pk=request.GET['crashid'])
            
            configuration = ProgramConfiguration(crashEntry.product.name, 
                                                 crashEntry.platform.name, 
                                                 crashEntry.os.name, 
                                                 crashEntry.product.version)
            
            crashInfo = CrashInfo.fromRawCrashData(crashEntry.rawStdout, 
                                                   crashEntry.rawStderr, 
                                                   configuration, 
                                                   crashEntry.rawCrashData)
            
            proposedSignature = str(crashInfo.createCrashSignature())
            proposedShortDesc = crashInfo.createShortSignature()
            
            context = RequestContext(request, { 'new' : True, 'bucket' : { 
                                                            'pk' : None, 
                                                            'bug' : None,
                                                            'signature' : proposedSignature,
                                                            'shortDescription' : proposedShortDesc,
                                                            } })
        else:
            context = RequestContext(request, { 'new' : True })
    else:
        raise SuspiciousOperation
        
    return render(request, 'signature_edit.html', context)

@login_required(login_url='/login/')
def deleteSignature(request, sigid):
    bucket = get_object_or_404(Bucket, pk=sigid)
    if request.method == 'POST':    
        # Make sure we remove this bucket from all crash entries referring to it,
        # otherwise these would be deleted as well through cascading.
        CrashEntry.objects.filter(bucket=bucket).update(bucket=None)
        
        bucket.delete()
        return redirect('crashmanager:signatures')
    elif request.method == 'GET':
        context = RequestContext(request, { 'bucket' : bucket })
        return render(request, 'signature_del.html', context)
    else:
        raise SuspiciousOperation
    
@login_required(login_url='/login/')
def viewSignature(request, sigid):
    bucket = get_object_or_404(Bucket, pk=sigid)
    count = len(CrashEntry.objects.filter(bucket=bucket))
    context = RequestContext(request, { 'bucket' : bucket, 'crashcount' : count })
    return render(request, 'signature_view.html', context)

@login_required(login_url='/login/')
def editSignature(request, sigid):
    if request.method == 'POST':
        bucket = get_object_or_404(Bucket, pk=sigid)
        bucket.signature = request.POST['signature']
        bucket.shortDescription = request.POST['shortDescription']
        #TODO: FIXME: Update bug here as well
        
        bucket.save()
        return redirect('crashmanager:sigview', sigid=bucket.pk)
    elif request.method == 'GET':
        if sigid != None:
            bucket = get_object_or_404(Bucket, pk=sigid)
            context = RequestContext(request, { 'bucket' : bucket })
        elif 'crashid' in request.GET:
            crashEntry = get_object_or_404(CrashEntry, pk=request.GET['crashid'])
            
            configuration = ProgramConfiguration(crashEntry.product.name, 
                                                 crashEntry.platform.name, 
                                                 crashEntry.os.name, 
                                                 crashEntry.product.version)
            
            crashInfo = CrashInfo.fromRawCrashData(crashEntry.rawStdout, 
                                                   crashEntry.rawStderr, 
                                                   configuration, 
                                                   crashEntry.rawCrashData)
            
            proposedSignature = str(crashInfo.createCrashSignature())
            proposedShortDesc = crashInfo.createShortSignature()
            
            context = RequestContext(request, { 'bucket' : { 
                                                            'pk' : None, 
                                                            'bug' : None,
                                                            'signature' : proposedSignature,
                                                            'shortDescription' : proposedShortDesc,
                                                            } })
        else:
            raise SuspiciousOperation
    else:
        raise SuspiciousOperation
        
    return render(request, 'signature_edit.html', context)

class CrashEntryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows adding/viewing CrashEntries
    """
    queryset = CrashEntry.objects.all()
    serializer_class = CrashEntrySerializer


class BucketViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows reading of signatures
    """
    queryset = Bucket.objects.all()
    serializer_class = BucketSerializer