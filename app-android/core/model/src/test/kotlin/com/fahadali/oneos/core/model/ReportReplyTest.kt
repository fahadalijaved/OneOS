package com.fahadali.oneos.core.model

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ReportReplyTest {
    @Test
    fun signinReplyGivesCodeAndLink() {
        val r = """{"code":"ab12","url":"https://t.me/OneOSBot?start=ab12","group":"https://t.me/TheoneOS","expiresIn":600}"""
        assertEquals("ab12" to "https://t.me/OneOSBot?start=ab12", ReportReply.signin(r))
        assertNull(ReportReply.signin("""{"code":"x","url":"https://evil.example/x"}"""))
        assertNull(ReportReply.signin("{}"))
    }

    @Test
    fun claimStatuses() {
        assertEquals(ReportReply.Claim.Waiting, ReportReply.claim(202, """{"waiting":true}"""))
        assertEquals(ReportReply.Claim.Expired, ReportReply.claim(404, """{"error":"unknown code"}"""))
        assertNull(ReportReply.claim(503, "{}"))
        assertEquals(
            ReportReply.Claim.Done("p1", "tester_one", true),
            ReportReply.claim(200, """{"pass":"p1","username":"tester_one","member":true,"group":"https://t.me/TheoneOS"}"""),
        )
        assertEquals(
            ReportReply.Claim.Done("p2", null, false),
            ReportReply.claim(200, """{"pass":"p2","username":null,"member":false}"""),
        )
        assertNull(ReportReply.claim(200, """{"member":true}"""))
    }

    @Test
    fun refusals() {
        assertEquals(ReportReply.Refusal.JOIN, ReportReply.refusal(403, """{"error":"not a member","join":true,"group":"g"}"""))
        assertEquals(ReportReply.Refusal.SIGN_IN, ReportReply.refusal(403, """{"error":"sign in","signin":true}"""))
        assertNull(ReportReply.refusal(403, """{"error":"bad key"}"""))
        assertNull(ReportReply.refusal(400, """{"join":true}"""))
        assertEquals("a \"b\"", ReportReply.string("""{"error":"a \"b\""}""", "error"))
    }
}
