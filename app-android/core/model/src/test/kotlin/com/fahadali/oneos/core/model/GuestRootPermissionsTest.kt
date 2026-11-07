package com.fahadali.oneos.core.model

import org.junit.Assert.*
import org.junit.Test

class GuestRootPermissionsTest {
    private val p=GuestRootPermissions
    private fun app(pkg:String,uid:Int,allowed:Boolean=false,label:String=pkg,system:Boolean=false)=GuestRootPermissions.App(pkg,uid,allowed,label,system)
    @Test fun parserRejectsInvalidGrantsAndDuplicates() {
        val rows=p.parse("com.test.app 10001 1\ncom.test.app 10001 0\n../escape 10002 1\ncom.other 9999 1\ncom.bad x 1\ncom.bad 10004 2\n")
        assertEquals(listOf(GuestRootPermissions.Grant("com.test.app",10001,true)),rows)
    }
    @Test fun sharedUidShowsEffectiveAccessAndPrefersUserApp() {
        val group=p.groups(listOf(app("com.system",10001,true,"System",true),app("com.user",10001,false,"User"))).single()
        assertTrue(group.allowed);assertFalse(group.system);assertEquals("com.user",group.primary.packageName);assertEquals(2,group.apps.size)
    }
    @Test fun filtersSearchEverySharedUidMember() {
        val groups=p.groups(listOf(app("com.visible",10001,false,"Photo"),app("com.hidden.match",10001,true,"Other"),app("com.second",10002,false,"Second")))
        assertEquals(10001,p.filter(groups,"hidden 10001",GuestRootPermissions.Access.ALLOWED,GuestRootPermissions.Kind.USER).single().uid)
        assertTrue(p.filter(groups,"Photo",GuestRootPermissions.Access.DENIED,GuestRootPermissions.Kind.ALL).isEmpty())
    }
    @Test fun kindAndAccessFiltersCombineWithoutMutatingGrants() {
        val groups=p.groups(listOf(app("com.user",10001,true,"User"),app("com.system",10002,false,"System",true)))
        assertEquals(10002,p.filter(groups,"",GuestRootPermissions.Access.DENIED,GuestRootPermissions.Kind.SYSTEM).single().uid)
        assertEquals(10001,p.filter(groups,"uSeR",GuestRootPermissions.Access.ALLOWED,GuestRootPermissions.Kind.ALL).single().uid)
        assertEquals(2,groups.size);assertTrue(groups.first { it.uid==10001 }.allowed)
    }
}
